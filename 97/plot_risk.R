plot_risk <- function(model_file = "cox_model.rds",
                      data_file = "prepared_data.rds",
                      output_prefix = "risk_plot",
                      plot_types = c("forest", "score_dist", "risk_strata", "nomogram"),
                      save_plot = TRUE,
                      return_plots = FALSE) {
  
  required_packages <- c("survival", "survminer", "ggplot2", "dplyr", "forestplot", "rms", "pROC")
  
  for (pkg in required_packages) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      warning(sprintf("Package '%s' is recommended. Some plots may not be available.", pkg))
    }
  }
  
  library(survival)
  library(survminer)
  library(ggplot2)
  library(dplyr)
  
  if (!file.exists(model_file)) {
    stop(sprintf("Model file not found: %s", model_file))
  }
  
  message(sprintf("Loading model from: %s", model_file))
  model_results <- readRDS(model_file)
  
  data <- model_results$data
  cox_model <- model_results$model
  
  plots <- list()
  
  if ("forest" %in% plot_types) {
    message("\n=== Hazard Ratio Forest Plot ===")
    
    hr_ci <- model_results$hr_ci
    hr_df <- as.data.frame(hr_ci)
    hr_df$Variable <- rownames(hr_df)
    rownames(hr_df) <- NULL
    
    hr_df <- hr_df %>%
      mutate(
        HR_text = sprintf("%.2f (%.2f-%.2f)", HR, HR_lower_95, HR_upper_95),
        p_text = ifelse(p_value < 0.001, "<0.001", sprintf("%.3f", p_value)),
        significance = case_when(
          p_value < 0.001 ~ "***",
          p_value < 0.01 ~ "**",
          p_value < 0.05 ~ "*",
          p_value < 0.1 ~ ".",
          TRUE ~ ""
        ),
        combined_text = ifelse(significance == "", 
                              HR_text,
                              sprintf("%s %s", HR_text, significance))
      )
    
    hr_df$Variable <- factor(hr_df$Variable, levels = rev(hr_df$Variable))
    
    x_max <- max(hr_df$HR_upper_95, na.rm = TRUE)
    x_range <- x_max - min(hr_df$HR_lower_95, na.rm = TRUE)
    x_axis_max <- x_max + x_range * 0.6
    
    forest_plot <- ggplot(hr_df, aes(x = HR, y = Variable)) +
      geom_vline(xintercept = 1, color = "red", linetype = "dashed", alpha = 0.7) +
      geom_errorbarh(aes(xmin = HR_lower_95, xmax = HR_upper_95), 
                     height = 0.3, color = "darkblue", alpha = 0.8, linewidth = 0.8) +
      geom_point(aes(size = -log10(p_value + 1e-10)), color = "darkblue", alpha = 0.9) +
      geom_text(aes(label = p_text, x = 0.12), 
                hjust = 0, size = 3.2, color = "gray40") +
      geom_text(aes(label = combined_text, x = x_max + x_range * 0.05), 
                hjust = 0, size = 3.5, fontface = "bold") +
      scale_x_log10(
        breaks = c(0.25, 0.5, 1, 2, 4, 8),
        limits = c(0.1, x_axis_max)
      ) +
      scale_size_continuous(range = c(2, 6)) +
      labs(
        title = "Hazard Ratio Forest Plot",
        subtitle = "Cox Proportional Hazards Model",
        x = "Hazard Ratio (95% CI, log scale)",
        y = "Covariate",
        caption = sprintf("C-index = %.3f | *** p<0.001, ** p<0.01, * p<0.05", model_results$c_index)
      ) +
      theme_minimal() +
      theme(
        legend.position = "none",
        panel.grid.minor = element_blank(),
        plot.title = element_text(hjust = 0.5, face = "bold"),
        plot.subtitle = element_text(hjust = 0.5),
        axis.text.y = element_text(size = 10, face = "bold"),
        plot.margin = margin(10, 10, 10, 10)
      )
    
    plots$forest <- forest_plot
    
    if (save_plot) {
      forest_file <- sprintf("%s_forest.pdf", output_prefix)
      ggsave(forest_file, plot = forest_plot, width = 12, height = 8)
      message(sprintf("Saved forest plot to: %s", forest_file))
      
      forest_file_png <- sprintf("%s_forest.png", output_prefix)
      ggsave(forest_file_png, plot = forest_plot, width = 12, height = 8, dpi = 300)
      message(sprintf("Saved forest plot (PNG) to: %s", forest_file_png))
    }
  }
  
  if ("score_dist" %in% plot_types) {
    message("\n=== Risk Score Distribution ===")
    
    linear_predictors <- predict(cox_model, type = "lp")
    risk_scores <- exp(linear_predictors)
    
    data$risk_score <- risk_scores
    data$linear_predictor <- linear_predictors
    data$event_status <- factor(data$event, levels = c(0, 1), labels = c("Censored", "Event"))
    
    dist_plot <- ggplot(data, aes(x = risk_score, fill = event_status)) +
      geom_density(alpha = 0.6, color = "black") +
      geom_rug(aes(color = event_status), alpha = 0.5) +
      geom_vline(xintercept = median(risk_scores), 
                 color = "red", linetype = "dashed", size = 1, alpha = 0.7) +
      annotate("text", x = median(risk_scores), y = Inf, 
               label = sprintf("Median: %.2f", median(risk_scores)), 
               vjust = 2, hjust = -0.1, color = "red") +
      scale_fill_brewer(palette = "Set1") +
      scale_color_brewer(palette = "Set1") +
      labs(
        title = "Risk Score Distribution",
        subtitle = "Based on Cox Model Linear Predictor (exp(LP))",
        x = "Risk Score",
        y = "Density",
        fill = "Status",
        color = "Status"
      ) +
      theme_minimal() +
      theme(
        legend.position = "top",
        plot.title = element_text(hjust = 0.5, face = "bold"),
        plot.subtitle = element_text(hjust = 0.5)
      )
    
    plots$score_dist <- dist_plot
    
    if (save_plot) {
      dist_file <- sprintf("%s_score_dist.pdf", output_prefix)
      ggsave(dist_file, plot = dist_plot, width = 10, height = 7)
      message(sprintf("Saved score distribution plot to: %s", dist_file))
      
      dist_file_png <- sprintf("%s_score_dist.png", output_prefix)
      ggsave(dist_file_png, plot = dist_plot, width = 10, height = 7, dpi = 300)
      message(sprintf("Saved score distribution plot (PNG) to: %s", dist_file_png))
    }
    
    lp_plot <- ggplot(data, aes(x = linear_predictor, fill = event_status)) +
      geom_density(alpha = 0.6, color = "black") +
      geom_rug(aes(color = event_status), alpha = 0.5) +
      geom_vline(xintercept = 0, color = "red", linetype = "dashed", size = 1, alpha = 0.7) +
      scale_fill_brewer(palette = "Set1") +
      scale_color_brewer(palette = "Set1") +
      labs(
        title = "Linear Predictor Distribution",
        subtitle = "Cox Model Linear Predictor (LP)",
        x = "Linear Predictor",
        y = "Density",
        fill = "Status",
        color = "Status"
      ) +
      theme_minimal() +
      theme(
        legend.position = "top",
        plot.title = element_text(hjust = 0.5, face = "bold"),
        plot.subtitle = element_text(hjust = 0.5)
      )
    
    plots$linear_predictor <- lp_plot
  }
  
  if ("risk_strata" %in% plot_types) {
    message("\n=== Risk Strata Survival Curves ===")
    
    linear_predictors <- predict(cox_model, type = "lp")
    data$risk_score <- exp(linear_predictors)
    
    q1 <- quantile(data$risk_score, 1/3, type = 7)
    q2 <- quantile(data$risk_score, 2/3, type = 7)
    
    message(sprintf("Risk score summary: min=%.2f, median=%.2f, max=%.2f",
                    min(data$risk_score), median(data$risk_score), max(data$risk_score)))
    message(sprintf("Tertile cutoffs: 33%%=%.4f, 67%%=%.4f", q1, q2))
    
    data$risk_group <- cut(
      data$risk_score,
      breaks = c(-Inf, q1, q2, Inf),
      labels = c("Low Risk", "Medium Risk", "High Risk"),
      include.lowest = TRUE,
      right = TRUE
    )
    
    group_table <- table(data$risk_group, useNA = "ifany")
    message("Risk group distribution:")
    print(group_table)
    print(round(100 * prop.table(group_table), 1))
    
    if (any(is.na(data$risk_group))) {
      n_na <- sum(is.na(data$risk_group))
      warning(sprintf("Found %d observations with missing risk group", n_na))
    }
    
    km_risk <- survfit(Surv(time, event) ~ risk_group, data = data)
    
    strata_plot <- ggsurvplot(
      km_risk,
      data = data,
      risk.table = TRUE,
      pval = TRUE,
      pval.method = TRUE,
      conf.int = TRUE,
      surv.median.line = "hv",
      ggtheme = theme_minimal(),
      palette = c("blue", "orange", "red"),
      break.time.by = max(data$time) / 5,
      risk.table.y.text.col = TRUE,
      risk.table.y.text = FALSE,
      title = "Survival Curves by Risk Strata",
      subtitle = "Based on Cox Model Risk Score (Tertiles)",
      xlab = "Time",
      ylab = "Survival Probability"
    )
    
    plots$risk_strata <- strata_plot
    
    if (save_plot) {
      strata_file <- sprintf("%s_risk_strata.pdf", output_prefix)
      ggsave(strata_file, plot = strata_plot$plot, width = 10, height = 8)
      message(sprintf("Saved risk strata plot to: %s", strata_file))
      
      strata_file_png <- sprintf("%s_risk_strata.png", output_prefix)
      ggsave(strata_file_png, plot = strata_plot$plot, width = 10, height = 8, dpi = 300)
      message(sprintf("Saved risk strata plot (PNG) to: %s", strata_file_png))
    }
  }
  
  if ("nomogram" %in% plot_types && requireNamespace("rms", quietly = TRUE)) {
    message("\n=== Nomogram ===")
    
    library(rms)
    
    dd <- datadist(data)
    options(datadist = "dd")
    
    formula_str <- as.character(model_results$formula)
    f <- cph(as.formula(model_results$formula), data = data, x = TRUE, y = TRUE, surv = TRUE)
    
    surv <- Survival(f)
    
    time_points <- c(365, 365 * 2, 365 * 3)
    time_points <- time_points[time_points < max(data$time)]
    
    if (length(time_points) == 0) {
      time_points <- c(median(data$time) / 2, median(data$time), median(data$time) * 1.5)
    }
    
    if (save_plot) {
      nomo_file <- sprintf("%s_nomogram.pdf", output_prefix)
      pdf(nomo_file, width = 12, height = 10)
      
      plot(nomogram(f, fun = list(function(x) surv(time_points[1], x),
                                  function(x) surv(time_points[2], x),
                                  function(x) surv(time_points[3], x)),
                    funlabel = paste0("Survival at ", round(time_points / 365, 1), "y")),
           xfrac = 0.2)
      
      dev.off()
      message(sprintf("Saved nomogram to: %s", nomo_file))
    }
  }
  
  if (requireNamespace("pROC", quietly = TRUE)) {
    message("\n=== Time-dependent ROC Analysis ===")
    
    library(pROC)
    
    linear_predictors <- predict(cox_model, type = "lp")
    
    median_time <- median(data$time[data$event == 1], na.rm = TRUE)
    
    roc_data <- data.frame(
      time = data$time,
      event = data$event,
      score = linear_predictors
    )
    
    roc_data$time_status <- ifelse(roc_data$event == 1 & roc_data$time <= median_time, 1,
                                  ifelse(roc_data$time > median_time, 0, NA))
    
    roc_data_valid <- roc_data[complete.cases(roc_data$time_status), ]
    
    if (nrow(roc_data_valid) > 10 && length(unique(roc_data_valid$time_status)) > 1) {
      roc_obj <- roc(roc_data_valid$time_status, roc_data_valid$score)
      
      auc_value <- auc(roc_obj)
      message(sprintf("AUC at median time (%.1f): %.3f", median_time, auc_value))
      
      roc_df <- data.frame(
        Specificity = 1 - roc_obj$specificities,
        Sensitivity = roc_obj$sensitivities
      )
      
      roc_plot <- ggplot(roc_df, aes(x = Specificity, y = Sensitivity)) +
        geom_path(color = "darkblue", size = 1.2) +
        geom_abline(intercept = 0, slope = 1, color = "red", linetype = "dashed", alpha = 0.7) +
        annotate("text", x = 0.75, y = 0.25, 
                 label = sprintf("AUC = %.3f", auc_value), 
                 size = 5, fontface = "bold") +
        labs(
          title = "ROC Curve (Time-dependent)",
          subtitle = sprintf("Time point: %.1f units", median_time),
          x = "1 - Specificity",
          y = "Sensitivity"
        ) +
        theme_minimal() +
        theme(
          plot.title = element_text(hjust = 0.5, face = "bold"),
          plot.subtitle = element_text(hjust = 0.5),
          aspect.ratio = 1
        )
      
      plots$roc <- roc_plot
      
      if (save_plot) {
        roc_file <- sprintf("%s_roc.pdf", output_prefix)
        ggsave(roc_file, plot = roc_plot, width = 8, height = 8)
        message(sprintf("Saved ROC plot to: %s", roc_file))
      }
    } else {
      message("Insufficient data for ROC analysis")
    }
  }
  
  results <- list(
    plots = plots,
    data = data
  )
  
  if (return_plots) {
    return(results)
  } else {
    invisible(results)
  }
}

calculate_risk_groups <- function(model_results, data = NULL, n_groups = 3) {
  if (is.null(data)) {
    data <- model_results$data
  }
  
  cox_model <- model_results$model
  linear_predictors <- predict(cox_model, type = "lp", newdata = data)
  data$risk_score <- exp(linear_predictors)
  
  if (!n_groups %in% c(2, 3, 4)) {
    stop("n_groups must be 2, 3, or 4")
  }
  
  if (n_groups == 2) {
    probs <- c(0, 0.5, 1)
    group_labels <- c("Low", "High")
  } else if (n_groups == 3) {
    probs <- c(0, 1/3, 2/3, 1)
    group_labels <- c("Low", "Medium", "High")
  } else {
    probs <- c(0, 0.25, 0.5, 0.75, 1)
    group_labels <- c("Low", "Medium-Low", "Medium-High", "High")
  }
  
  quantiles <- quantile(data$risk_score, probs, type = 7, na.rm = TRUE)
  
  if (any(duplicated(quantiles))) {
    warning("Duplicated quantile values detected. Some groups may have zero observations.")
    print(quantiles)
  }
  
  data$risk_group <- cut(
    data$risk_score,
    breaks = quantiles,
    labels = group_labels,
    include.lowest = TRUE,
    right = TRUE
  )
  
  n_missing <- sum(is.na(data$risk_group))
  if (n_missing > 0) {
    warning(sprintf("%d observations not assigned to any group", n_missing))
  }
  
  message("Risk group distribution:")
  group_table <- table(data$risk_group, useNA = "ifany")
  print(group_table)
  
  return(data)
}

if (!interactive()) {
  args <- commandArgs(trailingOnly = TRUE)
  
  model_file <- if (length(args) >= 1) args[1] else "cox_model.rds"
  data_file <- if (length(args) >= 2) args[2] else "prepared_data.rds"
  output_prefix <- if (length(args) >= 3) args[3] else "risk_plot"
  plot_types_str <- if (length(args) >= 4) args[4] else "forest,score_dist,risk_strata"
  
  plot_types <- strsplit(plot_types_str, ",")[[1]]
  
  results <- plot_risk(
    model_file = model_file,
    data_file = data_file,
    output_prefix = output_prefix,
    plot_types = plot_types,
    save_plot = TRUE,
    return_plots = FALSE
  )
  
  message("\nRisk visualization complete!")
}
