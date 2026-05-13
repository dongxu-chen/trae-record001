package utils

object Validator {
  private val emailRegex = """^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z0-9]{1,}$""".r

  def isValidEmail(email: String): Boolean = {
    Option(email).flatMap(e => Option(e.trim)).filter(_.nonEmpty).exists { trimmed =>
      emailRegex.pattern.matcher(trimmed).matches() && !trimmed.contains("..")
    }
  }

  def validateEmail(email: String): Either[String, String] = {
    val trimmed = email.trim
    if (isValidEmail(trimmed)) {
      Right(trimmed)
    } else {
      Left(s"Invalid email format: $email")
    }
  }
}
