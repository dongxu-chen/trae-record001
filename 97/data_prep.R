data_prep <- function(input_file = NULL, output_file = "prepared_data.rds") {
  required_packages <- c("survival", "dplyr", "tidyr", "readr")
  
  for (pkg in required_packages) {
    if (!requireNamespace(pkg, quietly = TRUE)) {
      stop(sprintf("Package '%s' is required. Please install it first.", pkg))
    }
  }
  
  library(survival)
  library(dplyr)
  library(tidyr)
  library(readr)
  
  if (is.null(input_file)) {
    message("No input file provided, using simulated survival data...")
    set.seed(42)
    n <- 500
    
    data <- data.frame(
      age = rnorm(n, mean = 60, sd = 10),
      sex = factor(sample(c("male", "female"), n, replace = TRUE, prob = c(0.6, 0.4))),
      treatment = factor(sample(c("control", "treatment"), n, replace = TRUE, prob = c(0.5, 0.5))),
      biomarker = rnorm(n, mean = 5, sd = 2),
      stage = factor(sample(c("I", "II", "III", "IV"), n, replace = TRUE, 
                           prob = c(0.3, 0.3, 0.25, 0.15)))
    )
    
    linear_predictor <- 0.03 * data$age + 
      0.4 * (data$sex == "male") + 
      -0.5 * (data$treatment == "treatment") + 
      0.2 * data$biomarker +
      0.3 * (data$stage == "II") + 
      0.6 * (data$stage == "III") + 
      1.0 * (data$stage == "IV")
    
    hazard <- exp(linear_predictor)
    survival_time <- rexp(n, rate = hazard / 100)
    censoring_time <- runif(n, min = 0, max = 365 * 5)
    
    data$time <- pmin(survival_time, censoring_time)
    data$event <- as.integer(survival_time <= censoring_time)
    
    data$time[data$time < 1] <- 1
    data$time <- round(data$time)
    
  } else {
    message(sprintf("Loading data from: %s", input_file))
    
    ext <- tools::file_ext(input_file)
    if (ext %in% c("csv", "txt")) {
      data <- read_csv(input_file)
    } else if (ext %in% c("rda", "RData")) {
      load(input_file)
    } else if (ext == "rds") {
      data <- readRDS(input_file)
    } else {
      stop("Unsupported file format. Please use CSV, RDS, or RData.")
    }
    
    required_cols <- c("time", "event")
    missing_cols <- setdiff(required_cols, colnames(data))
    if (length(missing_cols) > 0) {
      stop(sprintf("Missing required columns: %s", paste(missing_cols, collapse = ", ")))
    }
    
    if (!is.numeric(data$time)) {
      stop("'time' column must be numeric.")
    }
    if (any(data$time <= 0, na.rm = TRUE)) {
      warning("Found non-positive time values. Setting to minimum positive value.")
      data$time[data$time <= 0] <- min(data$time[data$time > 0], na.rm = TRUE)
    }
    
    if (!is.numeric(data$event) || !all(data$event %in% c(0, 1), na.rm = TRUE)) {
      stop("'event' column must be numeric with values 0 (censored) or 1 (event).")
    }
  }
  
  message(sprintf("Initial data shape: %d rows, %d columns", nrow(data), ncol(data)))
  
  missing_before <- sum(is.na(data))
  data <- data %>%
    drop_na(time, event)
  
  for (col in colnames(data)) {
    if (is.numeric(data[[col]])) {
      data[[col]][is.na(data[[col]])] <- median(data[[col]], na.rm = TRUE)
    } else if (is.factor(data[[col]]) || is.character(data[[col]])) {
      mode_val <- names(which.max(table(data[[col]])))
      data[[col]][is.na(data[[col]])] <- mode_val
    }
  }
  
  missing_after <- sum(is.na(data))
  message(sprintf("Handled missing values: %d -> %d", missing_before, missing_after))
  
  if ("sex" %in% colnames(data) && !is.factor(data$sex)) {
    data$sex <- factor(data$sex)
  }
  if ("treatment" %in% colnames(data) && !is.factor(data$treatment)) {
    data$treatment <- factor(data$treatment)
  }
  if ("stage" %in% colnames(data) && !is.factor(data$stage)) {
    data$stage <- factor(data$stage, levels = c("I", "II", "III", "IV"), ordered = TRUE)
  }
  
  numeric_cols <- sapply(data, is.numeric)
  if (any(numeric_cols)) {
    for (col in names(numeric_cols)[numeric_cols]) {
      if (col %in% c("time", "event")) next
      
      q1 <- quantile(data[[col]], 0.25, na.rm = TRUE)
      q3 <- quantile(data[[col]], 0.75, na.rm = TRUE)
      iqr <- q3 - q1
      lower_bound <- q1 - 1.5 * iqr
      upper_bound <- q3 + 1.5 * iqr
      
      outliers <- data[[col]] < lower_bound | data[[col]] > upper_bound
      if (any(outliers, na.rm = TRUE)) {
        message(sprintf("Found %d outliers in %s. Winsorizing...", sum(outliers, na.rm = TRUE), col))
        data[[col]][data[[col]] < lower_bound] <- lower_bound
        data[[col]][data[[col]] > upper_bound] <- upper_bound
      }
    }
  }
  
  message(sprintf("Final data shape: %d rows, %d columns", nrow(data), ncol(data)))
  message(sprintf("Event rate: %.1f%%", 100 * mean(data$event)))
  message(sprintf("Median follow-up time: %.1f", median(data$time)))
  
  if (!is.null(output_file)) {
    saveRDS(data, file = output_file)
    message(sprintf("Saved prepared data to: %s", output_file))
  }
  
  return(data)
}

if (!interactive()) {
  args <- commandArgs(trailingOnly = TRUE)
  
  input_file <- if (length(args) >= 1) args[1] else NULL
  output_file <- if (length(args) >= 2) args[2] else "prepared_data.rds"
  
  prepared_data <- data_prep(input_file = input_file, output_file = output_file)
  print(summary(prepared_data))
}
