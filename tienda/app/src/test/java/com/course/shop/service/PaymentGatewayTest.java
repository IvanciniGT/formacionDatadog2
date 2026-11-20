package com.course.shop.service;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

/**
 * FLAKY ON PURPOSE, for the Test Optimization lab. It talks to the real PaymentGateway, which
 * rejects ~30 % of the charges at random: same code, same commit, and it passes or fails
 * depending on luck. Exactly what an integration test against a third-party sandbox does.
 *
 * Datadog's Auto Test Retries re-run it when it fails, so the pipeline stays green, and the
 * mix of pass and fail on one commit is what flags it as flaky in Test Optimization. The fix
 * (the exercise): mock the provider, or make the failure rate injectable.
 */
class PaymentGatewayTest {

    @Test
    void charging_a_customer_returns_a_payment_reference() {
        PaymentGateway gateway = new PaymentGateway(mock(Metrics.class));

        String reference = gateway.charge("ana", 49.90);

        assertThat(reference).startsWith("PAY-");
    }
}
