survival_curve <- function(data_file = "prepared_data.rds",
                           model_file = "cox_model.rds",
                           group_var = NULL,
                           output_prefix = "survival_curve",
                           plot_type = c("km", "adjusted", "both"),
                           save_plot = TRUE,
                           return_plot = FALSE) {
  
  required_packages <- c("survival", "survminer", "ggplot2", "dplyr", "ggsurvfit")
  
  for (pkg in required_packages) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      stop(sprintf("Package '%s' is required. Please install it first.", pkg))
    }
  }
  
  library(survival)
  library(survminer)
  library(ggplot2)
  library(dplyr)
  library(ggsurvfit)
  
  plot_type <- match.arg(plot_type)
  
  if (is.character(data_file)) {
    message(sprintf("Loading data from: %s", data_file))
    data <- readRDS(data_file)
  } else if (is.data.frame(data_file)) {
    data <- data_file
    message("Using provided data frame...")
  } else {
    stop("data_file must be a file path or data frame")
  }
  
  model_results <- NULL
  if (!is.null(model_file) && file.exists(model_file)) {
    message(sprintf("Loading Cox model from: %s", model_file))
    model_results <- readRDS(model_file)
  }
  
  if (is.null(group_var)) {
    factor_vars <- names(which(sapply(data, is.factor)))
    if (length(factor_vars) > 0) {
      group_var <- factor_vars[1]
      message(sprintf("No group variable specified. Using first factor: %s", group_var))
    } else {
      message("No factor variables found. Plotting overall survival curve.")
      group_var <- NULL
    }
  }
  
  if (!is.null(group_var) && !group_var %in% colnames(data)) {
    stop(sprintf("Group variable '%s' not found in data", group_var))
  }
  
  plots <- list()
  
  if (plot_type %in% c("km", "both")) {
    message("\n=== Kaplan-Meier Survival Curves ===")
    
    if (is.null(group_var)) {
      km_fit <- survfit(Surv(time, event) ~ 1, data = data)
      km_plot <- ggsurvplot(
        km_fit,
        data = data,
        risk.table = TRUE,
        pval = FALSE,
        conf.int = TRUE,
        surv.median.line = "hv",
        ggtheme = theme_minimal(),
        palette = "jco",
        break.time.by = max(data$time) / 5,
        risk.table.y.text.col = TRUE,
        risk.table.y.text = FALSE,
        title = "Overall Kaplan-Meier Survival Curve",
        xlab = "Time",
        ylab = "Survival Probability"
      )
    } else {
      formula_str <- sprintf("Surv(time, event) ~ %s", group_var)
      km_fit <- survfit(as.formula(formula_str), data = data)
      
      log_rank <- survdiff(as.formula(formula_str), data = data)
      p_value <- 1 - pchisq(log_rank$chisq, length(log_rank$n) - 1)
      
      km_plot <- ggsurvplot(
        km_fit,
        data = data,
        risk.table = TRUE,
        pval = TRUE,
        pval.method = TRUE,
        conf.int = TRUE,
        surv.median.line = "hv",
        ggtheme = theme_minimal(),
        palette = "jco",
        break.time.by = max(data$time) / 5,
        risk.table.y.text.col = TRUE,
        risk.table.y.text = FALSE,
        title = sprintf("Kaplan-Meier Survival Curves by %s", group_var),
        xlab = "Time",
        ylab = "Survival Probability"
      )
      
      message(sprintf("Log-rank test p-value: %.4f", p_value))
    }
    
    plots$km <- km_plot
    
    if (save_plot) {
      km_file <- sprintf("%s_km.pdf", output_prefix)
      ggsave(km_file, plot = km_plot$plot, width = 10, height = 8)
      message(sprintf("Saved KM plot to: %s", km_file))
      
      km_file_png <- sprintf("%s_km.png", output_prefix)
      ggsave(km_file_png, plot = km_plot$plot, width = 10, height = 8, dpi = 300)
      message(sprintf("Saved KM plot (PNG) to: %s", km_file_png))
    }
  }
  
  if (plot_type %in% c("adjusted", "both") && !is.null(model_results)) {
    message("\n=== Adjusted Survival Curves (Cox Model) ===")
    
    cox_model <- model_results$model
    model_data <- model_results$data
    
    if (is.null(group_var)) {
      message("No group variable for adjusted curves. Skipping adjusted plots.")
    } else if (!group_var %in% model_results$covariates) {
      message(sprintf("Group variable '%s' not in model covariates. Skipping adjusted curves.", group_var))
    } else {
      group_values <- unique(model_data[[group_var]])
      group_values <- group_values[order(group_values)]
      n_groups <- length(group_values)
      
      message(sprintf("Creating adjusted curves for %d groups of '%s'", n_groups, group_var))
      
      new_data_list <- lapply(seq_along(group_values), function(i) {
        gv <- group_values[i]
        nd <- model_data[1, , drop = FALSE]
        
        nd[[group_var]] <- gv
        
        other_covars <- setdiff(model_results$covariates, group_var)
        for (cov in other_covars) {
          if (is.factor(model_data[[cov]])) {
            ref_level <- levels(model_data[[cov]])[1]
            nd[[cov]] <- factor(ref_level, levels = levels(model_data[[cov]]))
          } else {
            nd[[cov]] <- median(model_data[[cov]], na.rm = TRUE)
          }
        }
        
        return(nd)
      })
      
      new_data <- do.call(rbind, new_data_list)
      rownames(new_data) <- NULL
      
      message("Reference values for adjustment:")
      ref_vals <- new_data[1, setdiff(model_results$covariates, group_var), drop = FALSE]
      print(ref_vals)
      
      surv_fit <- survfit(cox_model, newdata = new_data, se.fit = TRUE, conf.type = "log")
      
      group_labels <- as.character(group_values)
      if (is.factor(group_values)) {
        group_labels <- levels(group_values)[as.integer(group_values)]
      }
      names(surv_fit$strata) <- paste0(group_var, "=", group_labels)
      
      adjusted_plot <- ggsurvplot(
        surv_fit,
        data = model_data,
        risk.table = TRUE,
        conf.int = TRUE,
        conf.int.style = "step",
        ggtheme = theme_minimal(),
        palette = "jco",
        break.time.by = max(model_data$time) / 5,
        risk.table.y.text.col = TRUE,
        risk.table.y.text = FALSE,
        title = sprintf("Adjusted Survival Curves by %s (Cox Model)", group_var),
        subtitle = "Adjusted for other covariates at reference/median values",
        xlab = "Time",
        ylab = "Adjusted Survival Probability"
      )
      
      plots$adjusted <- adjusted_plot
      
      if (save_plot) {
        adj_file <- sprintf("%s_adjusted.pdf", output_prefix)
        ggsave(adj_file, plot = adjusted_plot$plot, width = 10, height = 8)
        message(sprintf("Saved adjusted plot to: %s", adj_file))
        
        adj_file_png <- sprintf("%s_adjusted.png", output_prefix)
        ggsave(adj_file_png, plot = adjusted_plot$plot, width = 10, height = 8, dpi = 300)
        message(sprintf("Saved adjusted plot (PNG) to: %s", adj_file_png))
      }
    }
  }
  
  if (!is.null(model_results) && save_plot) {
    message("\n=== Additional Diagnostic Plots ===")
    
    res_plot_file <- sprintf("%s_residuals.pdf", output_prefix)
    pdf(res_plot_file, width = 12, height = 10)
    
    par(mfrow = c(2, 2))
    
    zph_test <- model_results$zph_test
    plot(zph_test, main = "Schoenfeld Residuals (PH Assumption)")
    
    martingale_res <- model_results$martingale_residuals
    plot(martingale_res, main = "Martingale Residuals", xlab = "Index", ylab = "Residual")
    abline(h = 0, col = "red", lty = 2)
    
    deviance_res <- residuals(model_results$model, type = "deviance")
    plot(deviance_res, main = "Deviance Residuals", xlab = "Index", ylab = "Residual")
    abline(h = 0, col = "red", lty = 2)
    
    score_res <- residuals(model_results$model, type = "score")
    if (is.matrix(score_res) && ncol(score_res) > 0) {
      plot(score_res[, 1], main = sprintf("Score Residuals (%s)", colnames(score_res)[1]),
           xlab = "Index", ylab = "Residual")
      abline(h = 0, col = "red", lty = 2)
    }
    
    dev.off()
    message(sprintf("Saved diagnostic plots to: %s", res_plot_file))
  }
  
  results <- list(
    plots = plots,
    data = data,
    group_var = group_var
  )
  
  if (return_plot) {
    return(results)
  } else {
    invisible(results)
  }
}

plot_median_survival <- function(km_fit, group_var = "Group") {
  if (!inherits(km_fit, "survfit")) {
    stop("km_fit must be a survfit object")
  }
  
  surv_summary <- summary(km_fit)
  median_times <- surv_summary$table[, "median"]
  
  median_df <- data.frame(
    Group = names(median_times),
    Median_Survival = as.numeric(median_times)
  )
  
  p <- ggplot(median_df, aes(x = Group, y = Median_Survival, fill = Group)) +
    geom_bar(stat = "identity", alpha = 0.7, color = "black") +
    geom_text(aes(label = round(Median_Survival, 1)), vjust = -0.5, size = 3.5) +
    labs(
      title = "Median Survival Time by Group",
      x = group_var,
      y = "Median Survival Time"
    ) +
    theme_minimal() +
    theme(legend.position = "none") +
    scale_fill_jco()
  
  return(p)
}

if (!interactive()) {
  args <- commandArgs(trailingOnly = TRUE)
  
  data_file <- if (length(args) >= 1) args[1] else "prepared_data.rds"
  model_file <- if (length(args) >= 2) args[2] else "cox_model.rds"
  group_var <- if (length(args) >= 3) args[3] else NULL
  output_prefix <- if (length(args) >= 4) args[4] else "survival_curve"
  plot_type <- if (length(args) >= 5) args[5] else "both"
  
  results <- survival_curve(
    data_file = data_file,
    model_file = model_file,
    group_var = group_var,
    output_prefix = output_prefix,
    plot_type = plot_type,
    save_plot = TRUE,
    return_plot = FALSE
  )
  
  message("\nSurvival curve generation complete!")
}
