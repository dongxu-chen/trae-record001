package com.configcenter.admin.controller;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

@Controller
@RequestMapping("/")
public class AdminPageController {

    @Value("${config.server.url:http://localhost:8888}")
    private String configServerUrl;

    @GetMapping
    public String index(Model model) {
        model.addAttribute("configServerUrl", configServerUrl);
        return "index";
    }

    @GetMapping("/versions")
    public String versions(Model model) {
        model.addAttribute("configServerUrl", configServerUrl);
        return "versions";
    }

    @GetMapping("/gray")
    public String gray(Model model) {
        model.addAttribute("configServerUrl", configServerUrl);
        return "gray";
    }

    @GetMapping("/snapshots")
    public String snapshots(Model model) {
        model.addAttribute("configServerUrl", configServerUrl);
        return "snapshots";
    }

    @GetMapping("/audit")
    public String audit(Model model) {
        model.addAttribute("configServerUrl", configServerUrl);
        return "audit";
    }

    @GetMapping("/pre-validation")
    public String preValidation(Model model) {
        model.addAttribute("configServerUrl", configServerUrl);
        return "pre-validation";
    }

    @GetMapping("/dependencies")
    public String dependencies(Model model) {
        model.addAttribute("configServerUrl", configServerUrl);
        return "dependencies";
    }
}
