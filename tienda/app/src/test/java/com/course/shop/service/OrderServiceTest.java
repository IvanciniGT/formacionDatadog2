package com.course.shop.service;

import com.course.shop.domain.Order;
import com.course.shop.domain.Product;
import com.course.shop.repository.OrderRepository;
import com.course.shop.repository.ProductRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

import java.math.BigDecimal;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyDouble;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

/**
 * The order flow without a database or a real payment provider: repositories, gateway and
 * metrics are mocks, so each test decides what the "outside world" answers.
 */
class OrderServiceTest {

    private OrderRepository orders;
    private ProductRepository products;
    private PaymentGateway payments;
    private OrderService service;
    private Product keyboard;

    @BeforeEach
    void setUp() {
        orders = mock(OrderRepository.class);
        products = mock(ProductRepository.class);
        payments = mock(PaymentGateway.class);
        service = new OrderService(orders, products, payments, mock(Metrics.class));
        keyboard = product(1L, "Keyboard", "peripherals", "49.90", 5);
        when(products.findById(1L)).thenReturn(Optional.of(keyboard));
    }

    @Test
    void a_paid_order_is_saved_as_PAID_and_takes_the_units_out_of_stock() {
        Order order = service.place("ana", 1L, 2);

        assertThat(order.getStatus()).isEqualTo("PAID");
        assertThat(order.getTotal()).isEqualByComparingTo("99.80");
        assertThat(keyboard.getStock()).isEqualTo(3);
        verify(payments).charge("ana", 99.80);
        verify(orders).save(order);
    }

    @Test
    void a_rejected_payment_is_saved_as_PAYMENT_FAILED_answers_with_an_error_and_keeps_the_stock() {
        when(payments.charge(anyString(), anyDouble()))
                .thenThrow(new PaymentGateway.PaymentException("gateway timeout"));

        assertThatThrownBy(() -> service.place("ana", 1L, 2))
                .isInstanceOf(PaymentGateway.PaymentException.class);

        // The failed order is still recorded: it is what lets support find it later.
        ArgumentCaptor<Order> saved = ArgumentCaptor.forClass(Order.class);
        verify(orders).save(saved.capture());
        assertThat(saved.getValue().getStatus()).isEqualTo("PAYMENT_FAILED");
        assertThat(keyboard.getStock()).isEqualTo(5);
    }

    @Test
    void without_enough_stock_nothing_is_charged_and_nothing_is_saved() {
        assertThatThrownBy(() -> service.place("ana", 1L, 6))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("Not enough stock");

        verify(payments, never()).charge(anyString(), anyDouble());
        verify(orders, never()).save(any());
    }

    @Test
    void buying_exactly_the_last_units_is_allowed() {
        Order order = service.place("ana", 1L, 5);

        assertThat(order.getStatus()).isEqualTo("PAID");
        assertThat(keyboard.getStock()).isZero();
    }

    @Test
    void an_unknown_product_is_rejected_before_touching_the_payment_provider() {
        when(products.findById(999L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.place("ana", 999L, 1))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("999");

        verify(payments, never()).charge(anyString(), anyDouble());
    }

    /** Product has no public constructor or setters except stock: JPA fills it in production. */
    static Product product(Long id, String name, String category, String price, int stock) {
        Product p = new Product();
        ReflectionTestUtils.setField(p, "id", id);
        ReflectionTestUtils.setField(p, "name", name);
        ReflectionTestUtils.setField(p, "category", category);
        ReflectionTestUtils.setField(p, "price", new BigDecimal(price));
        p.setStock(stock);
        return p;
    }
}
