package services

import javax.inject._
import play.api.libs.mailer._
import play.api.Configuration
import scala.concurrent.{ExecutionContext, Future}
import play.api.Logger

@Singleton
class EmailService @Inject()(
  mailerClient: MailerClient,
  configuration: Configuration
)(implicit ec: ExecutionContext) {
  private val logger = Logger(this.getClass)
  private val fromEmail = configuration.getOptional[String]("play.mailer.from").getOrElse("no-reply@example.com")

  private def sendEmailWithRetry(
    email: Email,
    maxRetries: Int = 2
  ): Either[String, String] = {
    var lastError: Option[Exception] = None
    for (attempt <- 1 to maxRetries + 1) {
      try {
        mailerClient.send(email)
        logger.info(s"Email sent successfully to ${email.to.mkString(", ")} (attempt $attempt)")
        return Right(s"Email sent successfully to ${email.to.mkString(", ")}")
      } catch {
        case e: Exception =>
          lastError = Some(e)
          logger.warn(s"Failed to send email (attempt $attempt): ${e.getMessage}")
          if (attempt <= maxRetries) {
            Thread.sleep(1000 * attempt)
          }
      }
    }
    val errorMsg = s"Failed to send email after ${maxRetries + 1} attempts: ${lastError.map(_.getMessage).getOrElse("Unknown error")}"
    logger.error(errorMsg)
    Left(errorMsg)
  }

  def sendWelcomeEmail(to: String, unsubscribeToken: String, unsubscribeBaseUrl: String = "http://localhost:9000/api/unsubscribe/"): Either[String, String] = {
    val unsubscribeUrl = unsubscribeBaseUrl + unsubscribeToken
    val email = Email(
      subject = "Welcome to Our Newsletter",
      from = fromEmail,
      to = Seq(to),
      bodyHtml = Some(
        s"""<html>
          |<body>
          |<h1>Welcome!</h1>
          |<p>Thank you for subscribing to our newsletter.</p>
          |<p>If you wish to unsubscribe, click <a href="$unsubscribeUrl">here</a>.</p>
          |</body>
          |</html>""".stripMargin
      ),
      bodyText = Some(s"Welcome!\n\nThank you for subscribing to our newsletter.\n\nIf you wish to unsubscribe, visit: $unsubscribeUrl")
    )
    sendEmailWithRetry(email)
  }

  def sendWelcomeEmail(to: String): Either[String, String] = {
    sendWelcomeEmail(to, "")
  }

  def sendUnsubscribeEmail(to: String): Either[String, String] = {
    val email = Email(
      subject = "Successfully Unsubscribed",
      from = fromEmail,
      to = Seq(to),
      bodyHtml = Some(
        """<html>
          |<body>
          |<h1>Goodbye</h1>
          |<p>You have been successfully unsubscribed from our newsletter.</p>
          |</body>
          |</html>""".stripMargin
      ),
      bodyText = Some("Goodbye\n\nYou have been successfully unsubscribed from our newsletter.")
    )
    sendEmailWithRetry(email)
  }

  def sendWelcomeEmailAsync(to: String): Future[Either[String, String]] = Future {
    sendWelcomeEmail(to)
  }

  def sendUnsubscribeEmailAsync(to: String): Future[Either[String, String]] = Future {
    sendUnsubscribeEmail(to)
  }
}
