package com.course.shop.web;

import com.course.shop.service.PaymentGateway;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Which HTTP status each failure becomes. It matters beyond the API: APM counts only 5xx as
 * errors, so this mapping decides what the error-rate monitors and the SLOs see.
 */
class ApiExceptionHandlerTest {

    private final ApiExceptionHandler handler = new ApiExceptionHandler();

    @Test
    void a_rejected_payment_is_a_502_bad_gateway() {
        var response = handler.payment(new PaymentGateway.PaymentException("gateway timeout"));
        assertThat(response.getStatusCode().value()).isEqualTo(502);
        assertThat(response.getBody()).containsEntry("error", "gateway timeout");
    }

    @Test
    void an_unknown_product_is_a_404() {
        assertThat(handler.notFound(new IllegalArgumentException("Product 999 does not exist"))
                .getStatusCode().value()).isEqualTo(404);
    }

    @Test
    void out_of_stock_is_a_409_and_not_an_error_in_APM() {
        assertThat(handler.conflict(new IllegalStateException("Not enough stock for Keyboard"))
                .getStatusCode().value()).isEqualTo(409);
    }

    @Test
    void the_demo_failure_of_api_error_stays_a_500() {
        assertThat(handler.conflict(new IllegalStateException("Boom! simulated failure"))
                .getStatusCode().value()).isEqualTo(500);
    }
}
