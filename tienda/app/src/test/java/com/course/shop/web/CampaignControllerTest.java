package com.course.shop.web;

import com.course.shop.service.Metrics;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class CampaignControllerTest {

    private final Metrics metrics = mock(Metrics.class);
    private final CampaignController controller = new CampaignController(metrics);

    @Test
    void activating_a_campaign_leaves_a_business_event_tagged_for_the_dashboard() {
        assertThat(controller.activate("black-friday")).containsEntry("status", "active");

        // evento:negocio is what the dashboard overlay filters by: without it the bar never shows.
        verify(metrics).businessEvent(contains("black-friday"), anyString(),
                eq("evento:negocio"), eq("campaign:black-friday"));
        verify(metrics).campaignActivated("black-friday");
    }

    @Test
    void a_name_that_is_not_a_valid_tag_is_rejected_and_sends_nothing() {
        assertThatThrownBy(() -> controller.activate("Black Friday!"))
                .isInstanceOf(IllegalArgumentException.class);

        verifyNoInteractions(metrics);
    }
}
