simulate_competing_risk <- function(n = 500,
                                     n_causes = 3,
                                     cause_names = c("Event of Interest", "Competing Risk 1", "Competing Risk 2"),
                                     seed = 42,
                                     output_file = NULL) {
  
  required_packages <- c("survival", "dplyr", "tidyr")
  
  for (pkg in required_packages) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      stop(sprintf("Package '%s' is required. Please install it first.", pkg))
    }
  }
  
  library(survival)
  library(dplyr)
  library(tidyr)
  
  set.seed(seed)
  
  message(sprintf("Simulating competing risks data: %d subjects, %d causes", n, n_causes))
  
  if (length(cause_names) != n_causes) {
    stop("cause_names length must equal n_causes")
  }
  
  data <- data.frame(
    id = 1:n,
    age = rnorm(n, mean = 60, sd = 10),
    sex = factor(sample(c("male", "female"), n, replace = TRUE, prob = c(0.6, 0.4))),
    treatment = factor(sample(c("control", "treatment"), n, replace = TRUE, prob = c(0.5, 0.5))),
    biomarker = rnorm(n, mean = 5, sd = 2),
    stringsAsFactors = FALSE
  )
  
  message(sprintf("Generating outcomes for %d competing causes...", n_causes))
  
  cause_times <- matrix(NA, nrow = n, ncol = n_causes)
  
  for (cause in 1:n_causes) {
    if (cause == 1) {
      lp <- 0.03 * data$age +
        0.4 * (data$sex == "male") +
        -0.5 * (data$treatment == "treatment") +
        0.2 * data$biomarker
    } else if (cause == 2) {
      lp <- 0.02 * data$age +
        0.2 * (data$sex == "male") +
        0.1 * data$biomarker
    } else {
      lp <- 0.01 * data$age +
        0.1 * (data$sex == "female") +
        0.05 * data$biomarker
    }
    
    hazard <- exp(lp) / 100
    cause_times[, cause] <- rexp(n, rate = hazard)
  }
  
  event_cause <- apply(cause_times, 1, which.min)
  event_time <- apply(cause_times, 1, min)
  
  censoring_rate <- 0.2
  censoring_time <- runif(n, min = 0, max = 365 * 5)
  
  data$time <- pmin(event_time, censoring_time)
  data$event <- as.integer(event_time <= censoring_time)
  data$event_type <- ifelse(data$event == 1, event_cause, 0)
  
  data$time[data$time < 1] <- 1
  data$time <- round(data$time)
  
  data$event_type_label <- factor(
    data$event_type,
    levels = 0:n_causes,
    labels = c("Censored", cause_names)
  )
  
  message("\n=== Event Type Distribution ===")
  event_table <- table(data$event_type_label)
  print(event_table)
  print(round(100 * prop.table(event_table), 1))
  
  message(sprintf("\nOverall event rate: %.1f%%", 100 * mean(data$event)))
  
  if (n_causes > 1) {
    for (cause in 1:n_causes) {
      cause_data <- data[data$event_type == cause | data$event_type == 0, ]
      message(sprintf("Cause %d (%s): %d events, %.1f%%",
                      cause, cause_names[cause],
                      sum(data$event_type == cause),
                      100 * sum(data$event_type == cause) / n))
    }
  }
  
  results <- list(
    data = data,
    n = n,
    n_causes = n_causes,
    cause_names = cause_names,
    event_table = event_table,
    seed = seed
  )
  
  if (!is.null(output_file)) {
    saveRDS(results, file = output_file)
    message(sprintf("\nSaved competing risks data to: %s", output_file))
  }
  
  return(results)
}

fit_cause_specific_cox <- function(data,
                                   cause_of_interest = 1,
                                   covariates = NULL,
                                   time_col = "time",
                                   event_col = "event_type",
                                   output_file = NULL) {
  
  required_packages <- c("survival", "dplyr")
  
  for (pkg in required_packages) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      stop(sprintf("Package '%s' is required. Please install it first.", pkg))
    }
  }
  
  library(survival)
  library(dplyr)
  
  message(sprintf("Fitting cause-specific Cox model for cause %d", cause_of_interest))
  
  if (is.null(covariates)) {
    covariates <- setdiff(colnames(data), c(time_col, event_col, "id", "event", "event_type_label"))
    message(sprintf("Using all available covariates: %s", paste(covariates, collapse = ", ")))
  }
  
  data_analysis <- data[, c(time_col, event_col, covariates), drop = FALSE]
  data_analysis <- data_analysis[complete.cases(data_analysis), ]
  
  data_cause <- data_analysis
  data_cause$event_cause <- as.integer(data_analysis[[event_col]] == cause_of_interest)
  
  message(sprintf("Data: %d subjects, %d events of interest", 
                  nrow(data_cause), sum(data_cause$event_cause)))
  
  formula_str <- sprintf("Surv(%s, event_cause) ~ %s", 
                         time_col, paste(covariates, collapse = " + "))
  formula_obj <- as.formula(formula_str)
  
  message(sprintf("Model formula: %s", formula_str))
  
  cox_model <- coxph(formula_obj, data = data_cause, ties = "efron")
  
  message("\n=== Model Summary ===")
  print(summary(cox_model))
  
  model_summary <- summary(cox_model)
  
  hr_ci <- cbind(
    HR = exp(coef(cox_model)),
    model_summary$conf.int[, c("lower .95", "upper .95")],
    p.value = model_summary$coefficients[, "Pr(>|z|)"]
  )
  colnames(hr_ci) <- c("HR", "HR_lower_95", "HR_upper_95", "p_value")
  
  message("\n=== Cause-Specific Hazard Ratios ===")
  print(hr_ci)
  
  c_index <- model_summary$concordance["C"]
  message(sprintf("\nC-index: %.3f", c_index))
  
  results <- list(
    model = cox_model,
    formula = formula_obj,
    formula_str = formula_str,
    hr_ci = hr_ci,
    cause_of_interest = cause_of_interest,
    c_index = as.numeric(c_index),
    data = data_cause,
    covariates = covariates,
    model_type = "cause_specific"
  )
  
  if (!is.null(output_file)) {
    saveRDS(results, file = output_file)
    message(sprintf("\nSaved cause-specific model to: %s", output_file))
  }
  
  return(results)
}

fit_finegray <- function(data,
                         cause_of_interest = 1,
                         covariates = NULL,
                         time_col = "time",
                         event_col = "event_type",
                         output_file = NULL) {
  
  required_packages <- c("survival", "cmprsk", "dplyr")
  
  for (pkg in required_packages) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      stop(sprintf("Package '%s' is required for Fine-Gray model. Install with: install.packages('%s')", pkg, pkg))
    }
  }
  
  library(survival)
  library(cmprsk)
  library(dplyr)
  
  message(sprintf("Fitting Fine-Gray model for cause %d (subdistribution hazards)", cause_of_interest))
  
  if (is.null(covariates)) {
    covariates <- setdiff(colnames(data), c(time_col, event_col, "id", "event", "event_type_label"))
    message(sprintf("Using all available covariates: %s", paste(covariates, collapse = ", ")))
  }
  
  model_data <- data[, c(time_col, event_col, covariates), drop = FALSE]
  model_data <- model_data[complete.cases(model_data), ]
  
  ftime <- model_data[[time_col]]
  fstatus <- model_data[[event_col]]
  
  cov_matrix <- model.matrix(as.formula(sprintf("~ %s", paste(covariates, collapse = " + "))), 
                             data = model_data)[, -1, drop = FALSE]
  
  message(sprintf("Data: %d subjects", nrow(model_data)))
  message(sprintf("Covariates: %d", ncol(cov_matrix)))
  
  fg_model <- crr(ftime = ftime, 
                  fstatus = fstatus, 
                  cov1 = cov_matrix,
                  failcode = cause_of_interest,
                  cencode = 0)
  
  message("\n=== Fine-Gray Model Summary ===")
  print(summary(fg_model))
  
  coef_table <- summary(fg_model)$coef
  
  hr_ci <- cbind(
    HR = exp(coef_table[, "coef"]),
    HR_lower_95 = exp(coef_table[, "coef"] - 1.96 * coef_table[, "se(coef)"]),
    HR_upper_95 = exp(coef_table[, "coef"] + 1.96 * coef_table[, "se(coef)"]),
    p_value = coef_table[, "p-value"]
  )
  rownames(hr_ci) <- rownames(coef_table)
  
  message("\n=== Subdistribution Hazard Ratios ===")
  print(hr_ci)
  
  results <- list(
    model = fg_model,
    hr_ci = hr_ci,
    cause_of_interest = cause_of_interest,
    data = model_data,
    covariates = covariates,
    model_type = "fine_gray"
  )
  
  if (!is.null(output_file)) {
    saveRDS(results, file = output_file)
    message(sprintf("\nSaved Fine-Gray model to: %s", output_file))
  }
  
  return(results)
}

cuminc_curve <- function(data,
                         time_col = "time",
                         event_col = "event_type",
                         cause_names = NULL,
                         output_file = "cuminc_curve.pdf",
                         return_data = FALSE) {
  
  required_packages <- c("survival", "cmprsk", "ggplot2")
  
  for (pkg in required_packages) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      stop(sprintf("Package '%s' is required. Install with: install.packages('%s')", pkg, pkg))
    }
  }
  
  library(survival)
  library(cmprsk)
  library(ggplot2)
  
  message("Estimating cumulative incidence curves...")
  
  ftime <- data[[time_col]]
  fstatus <- data[[event_col]]
  
  unique_causes <- sort(unique(fstatus[fstatus != 0]))
  n_causes <- length(unique_causes)
  
  if (is.null(cause_names)) {
    cause_names <- paste("Cause", unique_causes)
  }
  
  cuminc_obj <- cuminc(ftime = ftime, fstatus = fstatus, cencode = 0)
  
  message("\n=== Cumulative Incidence at Key Time Points ===")
  
  time_points <- quantile(ftime[fstatus != 0], c(0.25, 0.5, 0.75))
  time_points <- unique(round(time_points))
  
  for (tp in time_points) {
    message(sprintf("\nTime = %d:", tp))
    for (cause in unique_causes) {
      cause_name <- cause_names[which(unique_causes == cause)]
      ci_obj <- cuminc_obj[[paste(cause, "0", sep = " ")]]
      idx <- findInterval(tp, ci_obj$time)
      if (idx > 0) {
        message(sprintf("  %s: %.3f", cause_name, ci_obj$est[idx]))
      }
    }
  }
  
  plot_data_list <- list()
  for (cause in unique_causes) {
    cause_idx <- which(unique_causes == cause)
    ci_obj <- cuminc_obj[[paste(cause, "0", sep = " ")]]
    
    plot_data_list[[cause_idx]] <- data.frame(
      time = ci_obj$time,
      est = ci_obj$est,
      var = ci_obj$var,
      cause = factor(cause_names[cause_idx], levels = cause_names)
    )
  }
  
  plot_data <- do.call(rbind, plot_data_list)
  
  p <- ggplot(plot_data, aes(x = time, y = est, color = cause)) +
    geom_step(size = 1.2) +
    labs(
      title = "Cumulative Incidence Curves (Competing Risks)",
      x = "Time",
      y = "Cumulative Incidence",
      color = "Event Type"
    ) +
    scale_color_brewer(palette = "Set1") +
    theme_minimal() +
    theme(
      plot.title = element_text(hjust = 0.5, face = "bold"),
      legend.position = "top"
    )
  
  ggsave(output_file, plot = p, width = 10, height = 7)
  message(sprintf("\nSaved cumulative incidence plot to: %s", output_file))
  
  results <- list(
    cuminc = cuminc_obj,
    plot_data = plot_data,
    plot = p,
    n_causes = n_causes,
    cause_names = cause_names
  )
  
  if (return_data) {
    return(results)
  } else {
    invisible(results)
  }
}

compare_cause_specific_vs_finegray <- function(data,
                                               cause_of_interest = 1,
                                               covariates = NULL,
                                               time_col = "time",
                                               event_col = "event_type",
                                               output_file = NULL) {
  
  required_packages <- c("survival", "cmprsk", "dplyr", "ggplot2")
  
  for (pkg in required_packages) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      stop(sprintf("Package '%s' is required. Please install it first.", pkg))
    }
  }
  
  message("Comparing cause-specific Cox vs Fine-Gray models...")
  
  cs_model <- fit_cause_specific_cox(
    data = data,
    cause_of_interest = cause_of_interest,
    covariates = covariates,
    time_col = time_col,
    event_col = event_col
  )
  
  fg_model <- fit_finegray(
    data = data,
    cause_of_interest = cause_of_interest,
    covariates = covariates,
    time_col = time_col,
    event_col = event_col
  )
  
  message("\n=== Model Comparison ===")
  
  cs_hr <- cs_model$hr_ci
  fg_hr <- fg_model$hr_ci
  
  common_vars <- intersect(rownames(cs_hr), rownames(fg_hr))
  
  comparison_df <- data.frame(
    Variable = common_vars,
    CS_HR = cs_hr[common_vars, "HR"],
    CS_Lower = cs_hr[common_vars, "HR_lower_95"],
    CS_Upper = cs_hr[common_vars, "HR_upper_95"],
    CS_p = cs_hr[common_vars, "p_value"],
    FG_HR = fg_hr[common_vars, "HR"],
    FG_Lower = fg_hr[common_vars, "HR_lower_95"],
    FG_Upper = fg_hr[common_vars, "HR_upper_95"],
    FG_p = fg_hr[common_vars, "p_value"]
  )
  
  rownames(comparison_df) <- NULL
  
  message("\nHazard Ratio Comparison:")
  print(comparison_df)
  
  comparison_df$HR_diff <- comparison_df$FG_HR - comparison_df$CS_HR
  
  message("\nInterpretation:")
  message("  - Cause-Specific (CS): Hazard among subjects at risk for this cause")
  message("  - Fine-Gray (FG): Subdistribution hazard (accounts for competing risks)")
  message("  - When competing risks are present, FG may be more appropriate for prediction")
  
  library(ggplot2)
  library(tidyr)
  
  plot_df <- comparison_df %>%
    select(Variable, CS_HR, FG_HR) %>%
    gather(Model, HR, -Variable)
  
  p <- ggplot(plot_df, aes(x = Variable, y = HR, color = Model, group = Model)) +
    geom_hline(yintercept = 1, color = "red", linetype = "dashed") +
    geom_point(position = position_dodge(0.3), size = 3) +
    geom_errorbar(data = comparison_df %>%
                    gather(Model, value, -Variable, -HR_diff) %>%
                    separate(Model, into = c("Model", "Metric"), sep = "_") %>%
                    spread(Metric, value),
                  aes(ymin = Lower, ymax = Upper),
                  position = position_dodge(0.3), width = 0.2) +
    coord_flip() +
    scale_y_log10() +
    labs(
      title = "Cause-Specific vs Fine-Gray Hazard Ratios",
      subtitle = sprintf("Cause of Interest: %d", cause_of_interest),
      x = "Variable",
      y = "Hazard Ratio (log scale)",
      color = "Model"
    ) +
    scale_color_brewer(palette = "Set1") +
    theme_minimal() +
    theme(
      plot.title = element_text(hjust = 0.5, face = "bold"),
      plot.subtitle = element_text(hjust = 0.5),
      legend.position = "top"
    )
  
  if (!is.null(output_file)) {
    ggsave(output_file, plot = p, width = 10, height = 8)
    message(sprintf("\nSaved comparison plot to: %s", output_file))
  }
  
  results <- list(
    cause_specific = cs_model,
    fine_gray = fg_model,
    comparison = comparison_df,
    plot = p
  )
  
  return(results)
}

if (!interactive()) {
  args <- commandArgs(trailingOnly = TRUE)
  
  if (length(args) == 0) {
    message("Usage:")
    message("  Rscript competing_risk.R simulate [n] [n_causes] [output_file]")
    message("  Rscript competing_risk.R cause_specific [data.rds] [cause] [output_file]")
    message("  Rscript competing_risk.R finegray [data.rds] [cause] [output_file]")
    message("  Rscript competing_risk.R cuminc [data.rds] [output_plot]")
    message("  Rscript competing_risk.R compare [data.rds] [cause] [output_plot]")
    quit(status = 0)
  }
  
  mode <- args[1]
  
  if (mode == "simulate") {
    n <- if (length(args) >= 2) as.integer(args[2]) else 500
    n_causes <- if (length(args) >= 3) as.integer(args[3]) else 3
    output <- if (length(args) >= 4) args[4] else "competing_risk_data.rds"
    
    results <- simulate_competing_risk(n = n, n_causes = n_causes, output_file = output)
    
  } else if (mode == "cause_specific") {
    input <- args[2]
    cause <- if (length(args) >= 3) as.integer(args[3]) else 1
    output <- if (length(args) >= 4) args[4] else "cause_specific_model.rds"
    
    if (grepl("\\.rds$", input)) {
      data_list <- readRDS(input)
      data <- if ("data" %in% names(data_list)) data_list$data else data_list
    }
    
    model <- fit_cause_specific_cox(data = data, cause_of_interest = cause, output_file = output)
    
  } else if (mode == "finegray") {
    input <- args[2]
    cause <- if (length(args) >= 3) as.integer(args[3]) else 1
    output <- if (length(args) >= 4) args[4] else "finegray_model.rds"
    
    if (grepl("\\.rds$", input)) {
      data_list <- readRDS(input)
      data <- if ("data" %in% names(data_list)) data_list$data else data_list
    }
    
    model <- fit_finegray(data = data, cause_of_interest = cause, output_file = output)
    
  } else if (mode == "cuminc") {
    input <- args[2]
    output <- if (length(args) >= 3) args[3] else "cuminc_curve.pdf"
    
    if (grepl("\\.rds$", input)) {
      data_list <- readRDS(input)
      data <- if ("data" %in% names(data_list)) data_list$data else data_list
    }
    
    cuminc_curve(data = data, output_file = output)
    
  } else if (mode == "compare") {
    input <- args[2]
    cause <- if (length(args) >= 3) as.integer(args[3]) else 1
    output <- if (length(args) >= 4) args[4] else "model_comparison.pdf"
    
    if (grepl("\\.rds$", input)) {
      data_list <- readRDS(input)
      data <- if ("data" %in% names(data_list)) data_list$data else data_list
    }
    
    comparison <- compare_cause_specific_vs_finegray(
      data = data, 
      cause_of_interest = cause,
      output_file = output
    )
    
  } else {
    stop(sprintf("Unknown mode: %s", mode))
  }
}
