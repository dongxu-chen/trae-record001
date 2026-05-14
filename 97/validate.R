cv_cox <- function(data_file = "prepared_data.rds",
                    model_file = "cox_model.rds",
                    n_folds = 5,
                    n_repeats = 1,
                    covariates = NULL,
                    time_points = NULL,
                    seed = 42,
                    output_file = "cv_results.rds",
                    save_plots = TRUE) {
  
  required_packages <- c("survival", "survminer", "dplyr", "ggplot2", "pec", "risksetROC")
  
  for (pkg in required_packages) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      warning(sprintf("Package '%s' recommended for full validation. Some features may be unavailable.", pkg))
    }
  }
  
  library(survival)
  library(dplyr)
  library(ggplot2)
  
  set.seed(seed)
  
  if (is.character(data_file)) {
    message(sprintf("Loading data from: %s", data_file))
    data <- readRDS(data_file)
  } else if (is.data.frame(data_file)) {
    data <- data_file
  } else {
    stop("data_file must be a file path or data frame")
  }
  
  if (is.null(covariates) && file.exists(model_file)) {
    message(sprintf("Loading covariates from model: %s", model_file))
    model_results <- readRDS(model_file)
    covariates <- model_results$covariates
  }
  
  if (is.null(covariates)) {
    covariates <- setdiff(colnames(data), c("time", "event", "id", "start", "stop"))
    message(sprintf("Using all available covariates: %s", paste(covariates, collapse = ", ")))
  }
  
  n_subjects <- nrow(data)
  message(sprintf("Starting %d-fold cross-validation with %d repeat(s)", n_folds, n_repeats))
  message(sprintf("Data: %d subjects, %d covariates", n_subjects, length(covariates)))
  message(sprintf("Event rate: %.1f%%", 100 * mean(data$event)))
  
  model_cols <- c("time", "event", covariates)
  data_model <- data[, model_cols, drop = FALSE]
  data_model <- data_model[complete.cases(data_model), ]
  n_subjects_clean <- nrow(data_model)
  
  if (n_subjects_clean < n_subjects) {
    message(sprintf("Removed %d rows with missing values", n_subjects - n_subjects_clean))
  }
  
  if (is.null(time_points)) {
    event_times <- data_model$time[data_model$event == 1]
    if (length(event_times) > 0) {
      time_points <- quantile(event_times, c(0.25, 0.5, 0.75))
      time_points <- unique(round(time_points))
    } else {
      time_points <- median(data_model$time)
    }
  }
  message(sprintf("Evaluation time points: %s", paste(time_points, collapse = ", ")))
  
  cv_results <- list()
  fold_metrics <- list()
  all_predictions <- list()
  
  for (rep in 1:n_repeats) {
    message(sprintf("\n=== Repeat %d/%d ===", rep, n_repeats))
    
    folds <- sample(rep(1:n_folds, length.out = n_subjects_clean))
    
    for (fold in 1:n_folds) {
      message(sprintf("  Fold %d/%d", fold, n_folds))
      
      train_idx <- folds != fold
      test_idx <- folds == fold
      
      train_data <- data_model[train_idx, , drop = FALSE]
      test_data <- data_model[test_idx, , drop = FALSE]
      
      message(sprintf("    Train: %d, Test: %d", nrow(train_data), nrow(test_data)))
      
      formula_str <- sprintf("Surv(time, event) ~ %s", paste(covariates, collapse = " + "))
      formula_obj <- as.formula(formula_str)
      
      train_model <- tryCatch({
        coxph(formula_obj, data = train_data, ties = "efron")
      }, error = function(e) {
        warning(sprintf("Model fitting failed in fold %d: %s", fold, e$message))
        return(NULL)
      })
      
      if (is.null(train_model)) next
      
      train_lp <- predict(train_model, type = "lp")
      train_risk <- exp(train_lp)
      
      test_lp <- predict(train_model, newdata = test_data, type = "lp")
      test_risk <- exp(test_lp)
      
      train_c <- summary(train_model)$concordance["C"]
      
      test_concordance <- tryCatch({
        surv_concordance <- survConcordance(Surv(time, event) ~ test_lp, data = test_data)
        surv_concordance$concordance
      }, error = function(e) NA)
      
      fold_result <- list(
        repeat = rep,
        fold = fold,
        train_cindex = as.numeric(train_c),
        test_cindex = as.numeric(test_concordance),
        train_coefs = coef(train_model),
        n_train = nrow(train_data),
        n_test = nrow(test_data)
      )
      
      predictions <- data.frame(
        repeat = rep,
        fold = fold,
        row_id = which(test_idx),
        time = test_data$time,
        event = test_data$event,
        lp = test_lp,
        risk = test_risk
      )
      
      fold_metrics[[length(fold_metrics) + 1]] <- fold_result
      all_predictions[[length(all_predictions) + 1]] <- predictions
    }
  }
  
  metrics_df <- do.call(rbind, lapply(fold_metrics, function(x) {
    data.frame(
      repeat = x$repeat,
      fold = x$fold,
      train_cindex = x$train_cindex,
      test_cindex = x$test_cindex,
      n_train = x$n_train,
      n_test = x$n_test
    )
  }))
  
  predictions_df <- do.call(rbind, all_predictions)
  
  message("\n=== Cross-Validation Results ===")
  
  message("\nC-index Summary:")
  c_summary <- data.frame(
    Metric = c("Train Mean", "Train SD", "Test Mean", "Test SD"),
    Value = c(
      mean(metrics_df$train_cindex, na.rm = TRUE),
      sd(metrics_df$train_cindex, na.rm = TRUE),
      mean(metrics_df$test_cindex, na.rm = TRUE),
      sd(metrics_df$test_cindex, na.rm = TRUE)
    )
  )
  print(c_summary)
  
  overfitting <- mean(metrics_df$train_cindex, na.rm = TRUE) - mean(metrics_df$test_cindex, na.rm = TRUE)
  message(sprintf("\nOverfitting (Train - Test): %.4f", overfitting))
  
  if (overfitting > 0.1) {
    warning("Model may be overfitting (difference > 0.1)")
  }
  
  if (save_plots) {
    message("\nGenerating validation plots...")
    
    cindex_plot <- ggplot(metrics_df, aes(x = factor(fold), y = test_cindex, fill = factor(repeat))) +
      geom_boxplot(alpha = 0.7, position = position_dodge(0.8)) +
      geom_hline(yintercept = mean(metrics_df$test_cindex, na.rm = TRUE), 
                 color = "red", linetype = "dashed", size = 1) +
      annotate("text", x = Inf, y = mean(metrics_df$test_cindex, na.rm = TRUE) + 0.02,
               label = sprintf("Mean = %.3f", mean(metrics_df$test_cindex, na.rm = TRUE)),
               hjust = 1.1, color = "red") +
      labs(
        title = sprintf("%d-Fold Cross-Validation C-index", n_folds),
        subtitle = ifelse(n_repeats > 1, sprintf("%d repeats", n_repeats), "Single repeat"),
        x = "Fold",
        y = "C-index",
        fill = "Repeat"
      ) +
      theme_minimal() +
      theme(
        plot.title = element_text(hjust = 0.5, face = "bold"),
        plot.subtitle = element_text(hjust = 0.5)
      ) +
      ylim(c(0.5, 1))
    
    ggsave("cv_cindex_plot.pdf", plot = cindex_plot, width = 10, height = 6)
    ggsave("cv_cindex_plot.png", plot = cindex_plot, width = 10, height = 6, dpi = 300)
    message("Saved: cv_cindex_plot.pdf/png")
  }
  
  results <- list(
    method = "k_fold_cv",
    n_folds = n_folds,
    n_repeats = n_repeats,
    time_points = time_points,
    metrics = metrics_df,
    predictions = predictions_df,
    c_summary = c_summary,
    overfitting = overfitting,
    covariates = covariates,
    seed = seed
  )
  
  if (!is.null(output_file)) {
    saveRDS(results, file = output_file)
    message(sprintf("\nSaved CV results to: %s", output_file))
  }
  
  return(results)
}

bootstrap_cox <- function(data_file = "prepared_data.rds",
                          model_file = "cox_model.rds",
                          n_boot = 100,
                          covariates = NULL,
                          seed = 42,
                          output_file = "bootstrap_results.rds",
                          save_plots = TRUE) {
  
  required_packages <- c("survival", "dplyr", "ggplot2", "boot")
  
  for (pkg in required_packages) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      warning(sprintf("Package '%s' recommended for bootstrap.", pkg))
    }
  }
  
  library(survival)
  library(dplyr)
  library(ggplot2)
  
  set.seed(seed)
  
  if (is.character(data_file)) {
    message(sprintf("Loading data from: %s", data_file))
    data <- readRDS(data_file)
  } else if (is.data.frame(data_file)) {
    data <- data_file
  } else {
    stop("data_file must be a file path or data frame")
  }
  
  if (is.null(covariates) && file.exists(model_file)) {
    message(sprintf("Loading covariates from model: %s", model_file))
    model_results <- readRDS(model_file)
    covariates <- model_results$covariates
  }
  
  if (is.null(covariates)) {
    covariates <- setdiff(colnames(data), c("time", "event", "id", "start", "stop"))
  }
  
  n_subjects <- nrow(data)
  message(sprintf("Starting bootstrap validation: %d resamples", n_boot))
  message(sprintf("Data: %d subjects, %d covariates", n_subjects, length(covariates)))
  
  model_cols <- c("time", "event", covariates)
  data_model <- data[, model_cols, drop = FALSE]
  data_model <- data_model[complete.cases(data_model), ]
  n_subjects_clean <- nrow(data_model)
  
  formula_str <- sprintf("Surv(time, event) ~ %s", paste(covariates, collapse = " + "))
  formula_obj <- as.formula(formula_str)
  
  message(sprintf("Fitting original model..."))
  original_model <- coxph(formula_obj, data = data_model, ties = "efron")
  original_coef <- coef(original_model)
  original_hr <- exp(original_coef)
  original_c <- summary(original_model)$concordance["C"]
  
  message(sprintf("Original model C-index: %.4f", original_c))
  
  message("\nRunning bootstrap resamples...")
  
  boot_results <- list()
  boot_coefs <- matrix(NA, nrow = n_boot, ncol = length(original_coef))
  colnames(boot_coefs) <- names(original_coef)
  boot_cindex <- numeric(n_boot)
  boot_success <- logical(n_boot)
  
  pb <- txtProgressBar(min = 0, max = n_boot, style = 3)
  
  for (b in 1:n_boot) {
    boot_idx <- sample(1:n_subjects_clean, replace = TRUE)
    boot_data <- data_model[boot_idx, , drop = FALSE]
    
    boot_model <- tryCatch({
      coxph(formula_obj, data = boot_data, ties = "efron")
    }, error = function(e) {
      return(NULL)
    })
    
    if (!is.null(boot_model)) {
      boot_success[b] <- TRUE
      boot_coefs[b, names(coef(boot_model))] <- coef(boot_model)
      boot_cindex[b] <- summary(boot_model)$concordance["C"]
    } else {
      boot_success[b] <- FALSE
    }
    
    setTxtProgressBar(pb, b)
  }
  close(pb)
  
  n_success <- sum(boot_success)
  message(sprintf("\nBootstrap success rate: %.1f%% (%d/%d)", 
                  100 * n_success / n_boot, n_success, n_boot))
  
  boot_coefs_clean <- boot_coefs[boot_success, , drop = FALSE]
  boot_cindex_clean <- boot_cindex[boot_success]
  
  message("\n=== Bootstrap Results ===")
  
  coef_summary <- data.frame(
    Variable = names(original_coef),
    Original_Coef = as.numeric(original_coef),
    Original_HR = as.numeric(original_hr),
    Boot_Mean_Coef = apply(boot_coefs_clean, 2, mean, na.rm = TRUE),
    Boot_SE_Coef = apply(boot_coefs_clean, 2, sd, na.rm = TRUE),
    Boot_Mean_HR = exp(apply(boot_coefs_clean, 2, mean, na.rm = TRUE)),
    Boot_2.5_HR = exp(apply(boot_coefs_clean, 2, quantile, 0.025, na.rm = TRUE)),
    Boot_97.5_HR = exp(apply(boot_coefs_clean, 2, quantile, 0.975, na.rm = TRUE))
  )
  
  rownames(coef_summary) <- NULL
  message("\nCoefficient Bootstrap Summary:")
  print(coef_summary)
  
  cindex_summary <- data.frame(
    Metric = c("Original", "Bootstrap Mean", "Bootstrap SE", "Bootstrap 2.5%", "Bootstrap 97.5%"),
    Value = c(
      original_c,
      mean(boot_cindex_clean, na.rm = TRUE),
      sd(boot_cindex_clean, na.rm = TRUE),
      quantile(boot_cindex_clean, 0.025, na.rm = TRUE),
      quantile(boot_cindex_clean, 0.975, na.rm = TRUE)
    )
  )
  message("\nC-index Bootstrap Summary:")
  print(cindex_summary)
  
  if (save_plots) {
    message("\nGenerating bootstrap plots...")
    
    cindex_df <- data.frame(Cindex = boot_cindex_clean)
    
    cindex_dist <- ggplot(cindex_df, aes(x = Cindex)) +
      geom_histogram(aes(y = ..density..), bins = 30, fill = "steelblue", alpha = 0.7, color = "white") +
      geom_density(color = "darkred", size = 1) +
      geom_vline(xintercept = original_c, color = "red", linetype = "dashed", size = 1) +
      geom_vline(xintercept = quantile(boot_cindex_clean, c(0.025, 0.975), na.rm = TRUE),
                 color = "blue", linetype = "dotted", size = 1) +
      annotate("text", x = original_c, y = Inf, 
               label = sprintf("Original = %.3f", original_c),
               vjust = 2, hjust = -0.1, color = "red") +
      labs(
        title = sprintf("Bootstrap Distribution of C-index (n=%d)", n_success),
        subtitle = "Red dashed = Original, Blue dotted = 95% CI",
        x = "C-index",
        y = "Density"
      ) +
      theme_minimal() +
      theme(
        plot.title = element_text(hjust = 0.5, face = "bold"),
        plot.subtitle = element_text(hjust = 0.5)
      )
    
    ggsave("bootstrap_cindex_dist.pdf", plot = cindex_dist, width = 10, height = 6)
    ggsave("bootstrap_cindex_dist.png", plot = cindex_dist, width = 10, height = 6, dpi = 300)
    message("Saved: bootstrap_cindex_dist.pdf/png")
    
    if (length(original_coef) <= 10) {
      boot_coefs_long <- reshape2::melt(boot_coefs_clean)
      colnames(boot_coefs_long) <- c("Resample", "Variable", "Coefficient")
      
      coef_dist <- ggplot(boot_coefs_long, aes(x = Coefficient)) +
        geom_histogram(aes(y = ..density..), bins = 25, fill = "steelblue", alpha = 0.7) +
        geom_density(color = "darkred", size = 1) +
        facet_wrap(~ Variable, scales = "free") +
        labs(
          title = "Bootstrap Distributions of Coefficients",
          x = "Coefficient",
          y = "Density"
        ) +
        theme_minimal() +
        theme(
          plot.title = element_text(hjust = 0.5, face = "bold"),
          strip.text = element_text(face = "bold")
        )
      
      ggsave("bootstrap_coefs_dist.pdf", plot = coef_dist, width = 12, height = 10)
      message("Saved: bootstrap_coefs_dist.pdf")
    }
  }
  
  results <- list(
    method = "bootstrap",
    n_boot = n_boot,
    n_success = n_success,
    original_model = original_model,
    original_coef = original_coef,
    original_cindex = as.numeric(original_c),
    boot_coefs = boot_coefs_clean,
    boot_cindex = boot_cindex_clean,
    coef_summary = coef_summary,
    cindex_summary = cindex_summary,
    covariates = covariates,
    seed = seed
  )
  
  if (!is.null(output_file)) {
    saveRDS(results, file = output_file)
    message(sprintf("\nSaved bootstrap results to: %s", output_file))
  }
  
  return(results)
}

calibration_plot <- function(model_file = "cox_model.rds",
                             data_file = "prepared_data.rds",
                             time_points = NULL,
                             n_groups = 5,
                             output_file = "calibration_plot.pdf") {
  
  required_packages <- c("survival", "ggplot2", "pec")
  
  for (pkg in required_packages) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      stop(sprintf("Package '%s' is required for calibration.", pkg))
    }
  }
  
  library(survival)
  library(ggplot2)
  
  message("Creating calibration plot...")
  
  model_results <- readRDS(model_file)
  cox_model <- model_results$model
  
  if (is.character(data_file)) {
    data <- readRDS(data_file)
  } else {
    data <- data_file
  }
  
  if (is.null(time_points)) {
    event_times <- data$time[data$event == 1]
    time_points <- median(event_times)
  }
  
  lp <- predict(cox_model, newdata = data, type = "lp")
  risk_scores <- exp(lp)
  
  risk_groups <- cut(risk_scores, breaks = quantile(risk_scores, seq(0, 1, length.out = n_groups + 1)),
                     include.lowest = TRUE, labels = 1:n_groups)
  
  data$risk_group <- risk_groups
  
  km_by_group <- list()
  predicted_surv <- numeric(n_groups)
  
  for (g in 1:n_groups) {
    group_data <- data[data$risk_group == g, ]
    
    if (nrow(group_data) > 0) {
      km <- survfit(Surv(time, event) ~ 1, data = group_data)
      km_by_group[[g]] <- km
      
      idx <- findInterval(time_points, km$time)
      if (idx > 0) {
        predicted_surv[g] <- km$surv[idx]
      } else {
        predicted_surv[g] <- 1
      }
    }
  }
  
  mean_risk_by_group <- tapply(risk_scores, risk_groups, mean)
  n_by_group <- table(risk_groups)
  
  calib_df <- data.frame(
    Group = 1:n_groups,
    Mean_Risk = as.numeric(mean_risk_by_group),
    Observed_Survival = predicted_surv,
    N = as.numeric(n_by_group)
  )
  
  calib_df$Predicted_Survival <- exp(-calib_df$Mean_Risk * time_points / 100)
  
  p <- ggplot(calib_df, aes(x = Predicted_Survival, y = Observed_Survival)) +
    geom_abline(intercept = 0, slope = 1, color = "red", linetype = "dashed", size = 1) +
    geom_point(aes(size = N), color = "darkblue", alpha = 0.7) +
    geom_text(aes(label = Group), vjust = -1, size = 3) +
    geom_smooth(method = "lm", se = FALSE, color = "darkblue", size = 1) +
    labs(
      title = sprintf("Calibration Plot at Time = %d", time_points),
      subtitle = sprintf("%d risk groups by predicted risk", n_groups),
      x = "Predicted Survival Probability",
      y = "Observed Survival Probability (Kaplan-Meier)",
      size = "Group Size"
    ) +
    scale_x_continuous(limits = c(0, 1)) +
    scale_y_continuous(limits = c(0, 1)) +
    theme_minimal() +
    theme(
      plot.title = element_text(hjust = 0.5, face = "bold"),
      plot.subtitle = element_text(hjust = 0.5),
      aspect.ratio = 1
    )
  
  ggsave(output_file, plot = p, width = 8, height = 8)
  message(sprintf("Saved calibration plot to: %s", output_file))
  
  return(invisible(list(plot = p, data = calib_df)))
}

if (!interactive()) {
  args <- commandArgs(trailingOnly = TRUE)
  
  if (length(args) == 0) {
    message("Usage:")
    message("  Rscript validate.R cv [data.rds] [model.rds] [n_folds] [n_repeats]")
    message("  Rscript validate.R bootstrap [data.rds] [model.rds] [n_boot]")
    message("  Rscript validate.R calibration [model.rds] [data.rds] [time_point]")
    quit(status = 0)
  }
  
  mode <- args[1]
  
  if (mode == "cv") {
    data_file <- if (length(args) >= 2) args[2] else "prepared_data.rds"
    model_file <- if (length(args) >= 3) args[3] else "cox_model.rds"
    n_folds <- if (length(args) >= 4) as.integer(args[4]) else 5
    n_repeats <- if (length(args) >= 5) as.integer(args[5]) else 1
    
    cv_results <- cv_cox(
      data_file = data_file,
      model_file = model_file,
      n_folds = n_folds,
      n_repeats = n_repeats,
      save_plots = TRUE
    )
    
  } else if (mode == "bootstrap") {
    data_file <- if (length(args) >= 2) args[2] else "prepared_data.rds"
    model_file <- if (length(args) >= 3) args[3] else "cox_model.rds"
    n_boot <- if (length(args) >= 4) as.integer(args[4]) else 100
    
    boot_results <- bootstrap_cox(
      data_file = data_file,
      model_file = model_file,
      n_boot = n_boot,
      save_plots = TRUE
    )
    
  } else if (mode == "calibration") {
    model_file <- if (length(args) >= 2) args[2] else "cox_model.rds"
    data_file <- if (length(args) >= 3) args[3] else "prepared_data.rds"
    time_point <- if (length(args) >= 4) as.integer(args[4]) else NULL
    
    calibration_plot(
      model_file = model_file,
      data_file = data_file,
      time_points = time_point
    )
    
  } else {
    stop(sprintf("Unknown mode: %s", mode))
  }
}
