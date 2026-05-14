cox_fit <- function(data_file = "prepared_data.rds", 
                    covariates = NULL, 
                    output_file = "cox_model.rds",
                    tt_covariates = NULL,
                    tt_fun = NULL,
                    model_type = c("standard", "time_varying", "counting_process")) {
  
  model_type <- match.arg(model_type)
  
  required_packages <- c("survival", "survminer", "dplyr", "broom")
  
  for (pkg in required_packages) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      stop(sprintf("Package '%s' is required. Please install it first.", pkg))
    }
  }
  
  library(survival)
  library(survminer)
  library(dplyr)
  library(broom)
  
  if (is.character(data_file)) {
    message(sprintf("Loading data from: %s", data_file))
    data <- readRDS(data_file)
  } else if (is.data.frame(data_file)) {
    data <- data_file
    message("Using provided data frame...")
  } else {
    stop("data_file must be a file path or data frame")
  }
  
  message(sprintf("Input data: %d rows, %d columns", nrow(data), ncol(data)))
  
  required_cols <- c("time", "event")
  missing_cols <- setdiff(required_cols, colnames(data))
  if (length(missing_cols) > 0) {
    stop(sprintf("Missing required columns: %s", paste(missing_cols, collapse = ", ")))
  }
  
  if (is.null(covariates)) {
    covariates <- setdiff(colnames(data), c("time", "event"))
    message(sprintf("No covariates specified. Using all available: %s", 
                    paste(covariates, collapse = ", ")))
  }
  
  missing_covars <- setdiff(covariates, colnames(data))
  if (length(missing_covars) > 0) {
    stop(sprintf("Covariates not found in data: %s", paste(missing_covars, collapse = ", ")))
  }
  
  model_cols <- c("time", "event", covariates)
  data_model <- data[, model_cols, drop = FALSE]
  
  total_na <- sum(is.na(data_model))
  if (total_na > 0) {
    message(sprintf("Found %d missing values in model columns. Checking completeness...", total_na))
    
    row_na <- apply(data_model, 1, function(x) sum(is.na(x)))
    na_by_row <- table(row_na)
    message("Missing values per row:")
    print(na_by_row)
    
    complete_rows <- complete.cases(data_model)
    n_complete <- sum(complete_rows)
    n_removed <- nrow(data_model) - n_complete
    
    if (n_removed > 0) {
      if (n_removed / nrow(data_model) > 0.2) {
        warning(sprintf("Removing %d rows (%.1f%%) due to missing values. Consider imputation.", 
                        n_removed, 100 * n_removed / nrow(data_model)))
      } else {
        message(sprintf("Removing %d rows (%.1f%%) with missing values.", 
                        n_removed, 100 * n_removed / nrow(data_model)))
      }
      
      data_model <- data_model[complete_rows, , drop = FALSE]
    }
  }
  
  if (nrow(data_model) < 10) {
    stop(sprintf("Insufficient data after removing missing values: %d rows (need >= 10)", nrow(data_model)))
  }
  
  message(sprintf("Data for modeling: %d rows, %d columns", nrow(data_model), ncol(data_model)))
  message(sprintf("Event rate: %.1f%%", 100 * mean(data_model$event)))
  
  for (cov in covariates) {
    if (is.factor(data_model[[cov]])) {
      n_levels <- nlevels(data_model[[cov]])
      if (n_levels < 2) {
        warning(sprintf("Factor '%s' has only %d level. Removing from model.", cov, n_levels))
        covariates <- setdiff(covariates, cov)
      }
    } else if (is.numeric(data_model[[cov]])) {
      var_val <- var(data_model[[cov]], na.rm = TRUE)
      if (is.na(var_val) || var_val < 1e-10) {
        warning(sprintf("Numeric variable '%s' has near-zero variance. Removing from model.", cov))
        covariates <- setdiff(covariates, cov)
      }
    }
  }
  
  if (length(covariates) == 0) {
    stop("No valid covariates remaining after filtering. Cannot fit model.")
  }
  
  data <- data_model
  
  message(sprintf("\nModel type: %s", model_type))
  
  if (model_type == "time_varying" && !is.null(tt_covariates)) {
    message(sprintf("Time-varying covariates using tt() interface: %s", 
                    paste(tt_covariates, collapse = ", ")))
    
    invalid_tt <- setdiff(tt_covariates, covariates)
    if (length(invalid_tt) > 0) {
      stop(sprintf("tt_covariates not in covariates: %s", paste(invalid_tt, collapse = ", ")))
    }
    
    static_covariates <- setdiff(covariates, tt_covariates)
    
    tt_terms <- sapply(tt_covariates, function(cov) {
      if (!is.null(tt_fun) && cov %in% names(tt_fun)) {
        sprintf("tt(%s, %s)", cov, deparse(tt_fun[[cov]]))
      } else {
        sprintf("tt(%s)", cov)
      }
    })
    
    all_terms <- c(static_covariates, tt_terms)
    formula_str <- sprintf("Surv(time, event) ~ %s", paste(all_terms, collapse = " + "))
    
  } else if (model_type == "counting_process") {
    required_cp_cols <- c("start", "stop", "event")
    missing_cp <- setdiff(required_cp_cols, colnames(data))
    if (length(missing_cp) > 0) {
      stop(sprintf("Counting process format requires columns: %s. Missing: %s",
                   paste(required_cp_cols, collapse = ", "),
                   paste(missing_cp, collapse = ", ")))
    }
    
    message("Using counting process format (start, stop, event)")
    formula_str <- sprintf("Surv(start, stop, event) ~ %s", paste(covariates, collapse = " + "))
    
  } else {
    formula_str <- sprintf("Surv(time, event) ~ %s", paste(covariates, collapse = " + "))
  }
  
  formula_obj <- as.formula(formula_str)
  message(sprintf("Fitting Cox model: %s", formula_str))
  
  if (model_type == "time_varying" && !is.null(tt_covariates)) {
    if (is.null(tt_fun)) {
      message("Using default tt() function: identity transformation")
      cox_model <- coxph(formula_obj, data = data, ties = "efron")
    } else {
      message("Using custom tt() function(s)")
      cox_model <- coxph(formula_obj, data = data, ties = "efron", tt = tt_fun)
    }
  } else {
    cox_model <- coxph(formula_obj, data = data, ties = "efron")
  }
  
  message("\n=== Model Summary ===")
  print(summary(cox_model))
  
  model_summary <- summary(cox_model)
  
  message("\n=== Hazard Ratios (HR) and 95% CI ===")
  hr_ci <- cbind(
    HR = exp(coef(cox_model)),
    model_summary$conf.int[, c("lower .95", "upper .95")],
    p.value = model_summary$coefficients[, "Pr(>|z|)"]
  )
  colnames(hr_ci) <- c("HR", "HR_lower_95", "HR_upper_95", "p_value")
  print(hr_ci)
  
  message("\n=== Model Diagnostics ===")
  
  message("\n1. Proportional Hazards Assumption Test (Schoenfeld residuals):")
  zph_test <- cox.zph(cox_model)
  print(zph_test)
  
  ph_assumption_ok <- all(zph_test$table[, "p"] > 0.05, na.rm = TRUE)
  if (ph_assumption_ok) {
    message("Proportional hazards assumption satisfied (all p > 0.05)")
  } else {
    warning("Proportional hazards assumption may be violated for some variables")
  }
  
  message("\n2. Influential Observations:")
  dfbeta <- residuals(cox_model, type = "dfbeta")
  
  if (is.vector(dfbeta)) {
    dfbeta <- matrix(dfbeta, ncol = 1)
  }
  
  threshold <- qnorm(0.975) / sqrt(nrow(data))
  max_abs_dfbeta <- apply(abs(dfbeta), 1, max, na.rm = TRUE)
  influential <- which(max_abs_dfbeta > threshold)
  
  if (length(influential) > 0) {
    message(sprintf("Found %d potentially influential observations (threshold = %.4f)", 
                    length(influential), threshold))
    if (length(influential) <= 20) {
      print(influential)
    } else {
      print(head(influential, 20))
      message(sprintf("... and %d more", length(influential) - 20))
    }
  } else {
    message(sprintf("No influential observations detected (threshold = %.4f)", threshold))
  }
  
  message("\n3. Concordance Index (C-index):")
  c_index <- model_summary$concordance["C"]
  c_index_se <- model_summary$concordance["se(C)"]
  message(sprintf("C-index = %.3f (SE = %.3f)", c_index, c_index_se))
  
  message("\n4. Martingale Residuals Plot (for functional form assessment):")
  martingale_res <- residuals(cox_model, type = "martingale")
  martingale_summary <- data.frame(
    Mean = mean(martingale_res),
    SD = sd(martingale_res),
    Min = min(martingale_res),
    Max = max(martingale_res)
  )
  print(martingale_summary)
  
  model_results <- list(
    model = cox_model,
    formula = formula_obj,
    formula_str = formula_str,
    hr_ci = hr_ci,
    zph_test = zph_test,
    ph_assumption_ok = ph_assumption_ok,
    influential_obs = influential,
    c_index = c_index,
    c_index_se = c_index_se,
    martingale_residuals = martingale_res,
    data = data,
    covariates = covariates,
    model_type = model_type,
    tt_covariates = tt_covariates,
    tt_fun = tt_fun
  )
  
  if (!is.null(output_file)) {
    saveRDS(model_results, file = output_file)
    message(sprintf("\nSaved model results to: %s", output_file))
  }
  
  return(model_results)
}

extract_hr_table <- function(model_results, digits = 3) {
  if (!"hr_ci" %in% names(model_results)) {
    stop("Invalid model_results object")
  }
  
  hr_table <- as.data.frame(model_results$hr_ci)
  hr_table$Variable <- rownames(hr_table)
  rownames(hr_table) <- NULL
  
  hr_table <- hr_table[, c("Variable", "HR", "HR_lower_95", "HR_upper_95", "p_value")]
  
  hr_table$HR <- round(hr_table$HR, digits)
  hr_table$HR_lower_95 <- round(hr_table$HR_lower_95, digits)
  hr_table$HR_upper_95 <- round(hr_table$HR_upper_95, digits)
  
  hr_table$significance <- cut(hr_table$p_value,
                               breaks = c(-Inf, 0.001, 0.01, 0.05, 0.1, Inf),
                               labels = c("***", "**", "*", ".", "ns"))
  
  hr_table$p_value <- ifelse(hr_table$p_value < 0.001, "<0.001", 
                            round(hr_table$p_value, digits))
  
  return(hr_table)
}

if (!interactive()) {
  args <- commandArgs(trailingOnly = TRUE)
  
  data_file <- if (length(args) >= 1) args[1] else "prepared_data.rds"
  output_file <- if (length(args) >= 2) args[2] else "cox_model.rds"
  covariates <- if (length(args) >= 3) strsplit(args[3], ",")[[1]] else NULL
  tt_covariates <- if (length(args) >= 4 && args[4] != "") strsplit(args[4], ",")[[1]] else NULL
  model_type <- if (length(args) >= 5) args[5] else "standard"
  
  model_results <- cox_fit(
    data_file = data_file, 
    covariates = covariates, 
    output_file = output_file,
    tt_covariates = tt_covariates,
    model_type = model_type
  )
  
  message("\n=== HR Table ===")
  hr_table <- extract_hr_table(model_results)
  print(hr_table)
}
