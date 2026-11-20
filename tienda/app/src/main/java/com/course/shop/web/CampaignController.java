package com.course.shop.web;

import com.course.shop.service.Metrics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.regex.Pattern;

/**
 * Marketing switches on a promo campaign from the shop. Nothing changes in the code path: what
 * matters is the BUSINESS EVENT it leaves in Datadog, so that when orders or traffic jump the
 * dashboard shows why.
 */
@RestController
@RequestMapping("/api/campaign")
public class CampaignController {

    private static final Logger log = LoggerFactory.getLogger(CampaignController.class);
    // The name ends up as a tag value: keep it to what a tag accepts.
    private static final Pattern VALID_NAME = Pattern.compile("[a-z0-9-]{1,40}");
    private final Metrics metrics;

    public CampaignController(Metrics metrics) {
        this.metrics = metrics;
    }

    @PostMapping
    public Map<String, String> activate(@RequestParam(defaultValue = "black-friday") String name) {
        if (!VALID_NAME.matcher(name).matches()) {
            throw new IllegalArgumentException("Invalid campaign name: " + name);
        }
        metrics.businessEvent("Promo campaign activated: " + name,
                "Marketing activated the " + name + " campaign from the shop",
                "evento:negocio", "campaign:" + name);
        metrics.campaignActivated(name);
        log.info("Promo campaign activated campaign={}", name);
        return Map.of("campaign", name, "status", "active");
    }
}
