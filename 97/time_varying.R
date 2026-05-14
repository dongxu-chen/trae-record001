simulate_time_varying <- function(n = 500, 
                                   n_time_points = 3,
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
  message(sprintf("Simulating time-varying data: %d subjects, %d time points", n, n_time_points))
  
  id <- 1:n
  
  static_data <- data.frame(
    id = id,
    age = rnorm(n, mean = 60, sd = 10),
    sex = factor(sample(c("male", "female"), n, replace = TRUE, prob = c(0.6, 0.4))),
    treatment = factor(sample(c("control", "treatment"), n, replace = TRUE, prob = c(0.5, 0.5))),
    stringsAsFactors = FALSE
  )
  
  message("Creating time-varying covariates: biomarker, stage")
  
  tv_data_list <- lapply(id, function(i) {
    base_biomarker <- rnorm(1, mean = 5, sd = 2)
    base_stage <- sample(c("I", "II", "III", "IV"), 1, prob = c(0.4, 0.3, 0.2, 0.1))
    
    biomarker_values <- c(base_biomarker)
    stage_values <- c(base_stage)
    
    for (j in 2:n_time_points) {
      change <- rnorm(1, mean = 0.5, sd = 1)
      new_biomarker <- biomarker_values[j-1] + change
      biomarker_values <- c(biomarker_values, new_biomarker)
      
      if (runif(1) < 0.15) {
        current_idx <- which(c("I", "II", "III", "IV") == stage_values[j-1])
        if (current_idx < 4) {
          new_stage_idx <- current_idx + sample(0:1, 1)
          if (new_stage_idx > 4) new_stage_idx <- 4
          stage_values <- c(stage_values, c("I", "II", "III", "IV")[new_stage_idx])
        } else {
          stage_values <- c(stage_values, "IV")
        }
      } else {
        stage_values <- c(stage_values, stage_values[j-1])
      }
    }
    
    data.frame(
      id = rep(i, n_time_points),
      tp = 1:n_time_points,
      biomarker = biomarker_values,
      stage = factor(stage_values, levels = c("I", "II", "III", "IV"), ordered = TRUE)
    )
  })
  
  tv_data <- do.call(rbind, tv_data_list)
  
  tv_data_wide <- tv_data %>%
    pivot_wider(
      id_cols = id,
      names_from = tp,
      values_from = c(biomarker, stage),
      names_sep = "_tp"
    )
  
  wide_data <- merge(static_data, tv_data_wide, by = "id")
  
  message("Generating survival outcomes...")
  
  linear_predictor_base <- 0.03 * static_data$age +
    0.4 * (static_data$sex == "male") +
    -0.5 * (static_data$treatment == "treatment")
  
  tv_effects <- sapply(1:n, function(i) {
    tv_row <- tv_data[tv_data$id == i, ]
    mean(0.2 * tv_row$biomarker +
           0.3 * (tv_row$stage == "II") +
           0.6 * (tv_row$stage == "III") +
           1.0 * (tv_row$stage == "IV"))
  })
  
  linear_predictor <- linear_predictor_base + tv_effects
  
  hazard <- exp(linear_predictor)
  survival_time <- rexp(n, rate = hazard / 100)
  censoring_time <- runif(n, min = 0, max = 365 * 5)
  
  wide_data$time <- pmin(survival_time, censoring_time)
  wide_data$event <- as.integer(survival_time <= censoring_time)
  wide_data$time[wide_data$time < 1] <- 1
  wide_data$time <- round(wide_data$time)
  
  message(sprintf("Event rate: %.1f%%", 100 * mean(wide_data$event)))
  
  message("\n=== Creating Counting Process Format (start-stop) ===")
  
  interval_length <- 180
  max_time <- max(wide_data$time)
  n_intervals <- ceiling(max_time / interval_length)
  
  cp_list <- lapply(1:n, function(i) {
    subject <- wide_data[i, ]
    id_val <- subject$id
    event_time <- subject$time
    event_status <- subject$event
    
    starts <- seq(0, event_time, by = interval_length)
    if (starts[length(starts)] < event_time) {
      starts <- c(starts, event_time)
    }
    
    n_rows <- length(starts) - 1
    
    subject_cp <- data.frame(
      id = rep(id_val, n_rows),
      start = starts[1:n_rows],
      stop = starts[2:(n_rows + 1)]
    )
    
    subject_cp$age <- subject$age
    subject_cp$sex <- subject$sex
    subject_cp$treatment <- subject$treatment
    
    for (row in 1:n_rows) {
      tp_idx <- min(ceiling(subject_cp$start[row] / (event_time / n_time_points)) + 1, n_time_points)
      tp_idx <- max(tp_idx, 1)
      
      subject_cp$biomarker[row] <- subject[[paste0("biomarker_tp", tp_idx)]]
      subject_cp$stage[row] <- subject[[paste0("stage_tp", tp_idx)]]
    }
    
    subject_cp$event <- 0
    subject_cp$event[nrow(subject_cp)] <- event_status
    
    return(subject_cp)
  })
  
  cp_data <- do.call(rbind, cp_list)
  rownames(cp_data) <- NULL
  
  cp_data$stage <- factor(cp_data$stage, levels = c("I", "II", "III", "IV"), ordered = TRUE)
  
  message(sprintf("Counting process format: %d rows", nrow(cp_data)))
  message(sprintf("Unique subjects: %d", length(unique(cp_data$id))))
  
  cp_summary <- cp_data %>%
    group_by(id) %>%
    summarise(
      n_intervals = n(),
      total_time = sum(stop - start),
      event = max(event)
    )
  
  message(sprintf("Mean intervals per subject: %.2f", mean(cp_summary$n_intervals)))
  message(sprintf("Event rate in CP format: %.1f%%", 100 * mean(cp_summary$event)))
  
  results <- list(
    wide = wide_data,
    counting_process = cp_data,
    time_varying_long = tv_data,
    static = static_data,
    n = n,
    n_time_points = n_time_points,
    cp_summary = cp_summary
  )
  
  if (!is.null(output_file)) {
    saveRDS(results, file = output_file)
    message(sprintf("\nSaved time-varying data to: %s", output_file))
  }
  
  return(results)
}

wide_to_counting_process <- function(wide_data,
                                      id_col = "id",
                                      time_col = "time",
                                      event_col = "event",
                                      tv_covariates = NULL,
                                      static_covariates = NULL,
                                      interval_length = 180,
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
  
  message("Converting wide format to counting process (start-stop) format...")
  
  if (is.null(tv_covariates)) {
    tv_patterns <- grep("_tp\\d+$", colnames(wide_data), value = TRUE)
    if (length(tv_patterns) > 0) {
      tv_covariates <- unique(gsub("_tp\\d+$", "", tv_patterns))
      message(sprintf("Auto-detected time-varying covariates: %s", paste(tv_covariates, collapse = ", ")))
    } else {
      stop("No time-varying covariates detected. Please specify tv_covariates.")
    }
  }
  
  if (is.null(static_covariates)) {
    all_covars <- setdiff(colnames(wide_data), c(id_col, time_col, event_col))
    tv_cols <- unlist(lapply(tv_covariates, function(tv) grep(paste0(tv, "_tp"), colnames(wide_data), value = TRUE)))
    static_covariates <- setdiff(all_covars, tv_cols)
    message(sprintf("Auto-detected static covariates: %s", paste(static_covariates, collapse = ", ")))
  }
  
  n_subjects <- nrow(wide_data)
  
  n_tp_list <- sapply(tv_covariates, function(tv) {
    length(grep(paste0(tv, "_tp"), colnames(wide_data)))
  })
  n_tp <- max(n_tp_list)
  
  message(sprintf("Subjects: %d, Time points available: %d", n_subjects, n_tp))
  
  cp_list <- lapply(1:n_subjects, function(i) {
    subject <- wide_data[i, ]
    id_val <- subject[[id_col]]
    event_time <- subject[[time_col]]
    event_status <- subject[[event_col]]
    
    starts <- seq(0, event_time, by = interval_length)
    if (starts[length(starts)] < event_time) {
      starts <- c(starts, event_time)
    }
    
    n_rows <- length(starts) - 1
    
    subject_cp <- data.frame(
      id = rep(id_val, n_rows),
      start = starts[1:n_rows],
      stop = starts[2:(n_rows + 1)]
    )
    
    for (sc in static_covariates) {
      subject_cp[[sc]] <- subject[[sc]]
    }
    
    for (row in 1:n_rows) {
      mid_time <- (subject_cp$start[row] + subject_cp$stop[row]) / 2
      tp_idx <- min(ceiling(mid_time / (event_time / n_tp)) + 1, n_tp)
      tp_idx <- max(tp_idx, 1)
      
      for (tv in tv_covariates) {
        col_name <- paste0(tv, "_tp", tp_idx)
        if (col_name %in% colnames(subject)) {
          subject_cp[[tv]] <- subject[[col_name]]
        }
      }
    }
    
    subject_cp$event <- 0
    subject_cp$event[nrow(subject_cp)] <- event_status
    
    return(subject_cp)
  })
  
  cp_data <- do.call(rbind, cp_list)
  rownames(cp_data) <- NULL
  
  colnames(cp_data)[colnames(cp_data) == "id"] <- id_col
  
  message(sprintf("Converted to %d rows in counting process format", nrow(cp_data)))
  
  if (!is.null(output_file)) {
    saveRDS(cp_data, file = output_file)
    message(sprintf("Saved counting process data to: %s", output_file))
  }
  
  return(cp_data)
}

create_time_transform_functions <- function() {
  
  message("Available time transformation functions for tt() interface:")
  
  tt_identity <- function(x, t, ...) {
    x
  }
  
  tt_log <- function(x, t, ...) {
    x * log(t + 1)
  }
  
  tt_linear <- function(x, t, ...) {
    x * t
  }
  
  tt_threshold <- function(x, t, threshold = 365, ...) {
    x * as.numeric(t > threshold)
  }
  
  tt_spline <- function(x, t, knots = c(90, 365), ...) {
    require(splines)
    bs_t <- bs(t, knots = knots, degree = 3)
    x_mat <- matrix(x, ncol = 1) %*% matrix(1, nrow = 1, ncol = ncol(bs_t))
    x_mat * bs_t
  }
  
  tt_step <- function(x, t, cut_points = c(180, 365, 730), ...) {
    tp <- findInterval(t, cut_points)
    x * tp
  }
  
  functions <- list(
    identity = tt_identity,
    log = tt_log,
    linear = tt_linear,
    threshold = tt_threshold,
    spline = tt_spline,
    step = tt_step
  )
  
  message("  - identity: x (no transformation)")
  message("  - log: x * log(t+1)")
  message("  - linear: x * t")
  message("  - threshold: x * I(t > threshold)")
  message("  - spline: x * B-spline(t)")
  message("  - step: x * findInterval(t, cut_points)")
  
  return(functions)
}

check_proportional_hazards <- function(cox_model, plot = TRUE, output_file = NULL) {
  
  required_packages <- c("survival", "survminer", "ggplot2")
  
  for (pkg in required_packages) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      warning(sprintf("Package '%s' recommended for PH checking.", pkg))
    }
  }
  
  library(survival)
  
  message("Testing proportional hazards assumption...")
  
  zph_test <- cox.zph(cox_model)
  
  message("\n=== Schoenfeld Residuals Test ===")
  print(zph_test)
  
  global_p <- zph_test$table[nrow(zph_test$table), "p"]
  message(sprintf("\nGlobal test p-value: %.4f", global_p))
  
  if (global_p < 0.05) {
    warning("Proportional hazards assumption violated (p < 0.05)")
    message("Recommend using tt() interface or stratification")
  } else {
    message("Proportional hazards assumption satisfied")
  }
  
  if (plot && requireNamespace("survminer", quietly = TRUE)) {
    library(survminer)
    library(ggplot2)
    
    p <- ggcoxzph(zph_test, font.family = "sans")
    
    if (!is.null(output_file)) {
      ggsave(output_file, plot = p, width = 12, height = 10)
      message(sprintf("Saved PH diagnostic plot to: %s", output_file))
    }
    
    return(invisible(list(test = zph_test, plot = p)))
  }
  
  return(invisible(list(test = zph_test)))
}

fit_tt_model <- function(data,
                         static_covariates,
                         tt_covariates,
                         tt_fun = NULL,
                         time_col = "time",
                         event_col = "event",
                         output_file = NULL) {
  
  required_packages <- c("survival", "dplyr")
  
  for (pkg in required_packages) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      stop(sprintf("Package '%s' is required. Please install it first.", pkg))
    }
  }
  
  library(survival)
  library(dplyr)
  
  message("Fitting Cox model with tt() interface for time-varying effects...")
  message(sprintf("Static covariates: %s", paste(static_covariates, collapse = ", ")))
  message(sprintf("Time-varying covariates (tt): %s", paste(tt_covariates, collapse = ", ")))
  
  if (is.null(tt_fun)) {
    message("Using default tt() function (identity transformation)")
    tt_terms <- paste0("tt(", tt_covariates, ")")
  } else {
    message("Using custom tt() function(s)")
    tt_terms <- sapply(tt_covariates, function(cov) {
      if (cov %in% names(tt_fun)) {
        sprintf("tt(%s)", cov)
      } else {
        sprintf("tt(%s)", cov)
      }
    })
  }
  
  all_terms <- c(static_covariates, tt_terms)
  formula_str <- sprintf("Surv(%s, %s) ~ %s", time_col, event_col, paste(all_terms, collapse = " + "))
  formula_obj <- as.formula(formula_str)
  
  message(sprintf("Model formula: %s", formula_str))
  
  if (is.null(tt_fun)) {
    cox_model <- coxph(formula_obj, data = data, ties = "efron")
  } else {
    cox_model <- coxph(formula_obj, data = data, ties = "efron", tt = tt_fun)
  }
  
  message("\n=== Model Summary ===")
  print(summary(cox_model))
  
  model_summary <- summary(cox_model)
  
  hr_ci <- cbind(
    HR = exp(coef(cox_model)),
    model_summary$conf.int[, c("lower .95", "upper .95")],
    p.value = model_summary$coefficients[, "Pr(>|z|)"]
  )
  colnames(hr_ci) <- c("HR", "HR_lower_95", "HR_upper_95", "p_value")
  
  message("\n=== Hazard Ratios ===")
  print(hr_ci)
  
  results <- list(
    model = cox_model,
    formula = formula_obj,
    formula_str = formula_str,
    hr_ci = hr_ci,
    static_covariates = static_covariates,
    tt_covariates = tt_covariates,
    tt_fun = tt_fun,
    data = data,
    model_type = "time_varying_tt"
  )
  
  if (!is.null(output_file)) {
    saveRDS(results, file = output_file)
    message(sprintf("\nSaved tt() model to: %s", output_file))
  }
  
  return(results)
}

if (!interactive()) {
  args <- commandArgs(trailingOnly = TRUE)
  
  if (length(args) == 0) {
    message("Usage:")
    message("  Rscript time_varying.R simulate [n] [n_time_points] [output_file]")
    message("  Rscript time_varying.R convert [wide_data.rds] [output_file]")
    message("  Rscript time_varying.R check [model.rds] [output_plot]")
    message("  Rscript time_varying.R functions")
    quit(status = 0)
  }
  
  mode <- args[1]
  
  if (mode == "simulate") {
    n <- if (length(args) >= 2) as.integer(args[2]) else 500
    n_tp <- if (length(args) >= 3) as.integer(args[3]) else 3
    output <- if (length(args) >= 4) args[4] else "time_varying_data.rds"
    
    results <- simulate_time_varying(n = n, n_time_points = n_tp, output_file = output)
    
  } else if (mode == "convert") {
    input <- args[2]
    output <- if (length(args) >= 3) args[3] else "counting_process.rds"
    
    wide_data <- readRDS(input)
    cp_data <- wide_to_counting_process(wide_data, output_file = output)
    
  } else if (mode == "check") {
    model_file <- args[2]
    output <- if (length(args) >= 3) args[3] else "ph_diagnostic.pdf"
    
    model_results <- readRDS(model_file)
    check_proportional_hazards(model_results$model, plot = TRUE, output_file = output)
    
  } else if (mode == "functions") {
    create_time_transform_functions()
    
  } else {
    stop(sprintf("Unknown mode: %s", mode))
  }
}
