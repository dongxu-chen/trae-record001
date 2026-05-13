package controllers

import javax.inject._
import play.api._
import play.api.mvc._
import play.api.libs.json._
import services.EmailService
import repositories.{SubscriberRepository, SubscriberRecord}
import utils.Validator

@Singleton
class SubscribeController @Inject()(
  val controllerComponents: ControllerComponents,
  emailService: EmailService,
  subscriberRepository: SubscriberRepository
) extends BaseController {

  private val logger = Logger(this.getClass)

  implicit val subscriberRecordWrites: Writes[SubscriberRecord] = Json.writes[SubscriberRecord]

  private def subscriberToJson(subscriber: repositories.Subscriber): JsObject = {
    Json.obj(
      "email" -> subscriber.email,
      "unsubscribeToken" -> subscriber.unsubscribeToken,
      "subscribedAt" -> subscriber.subscribedAt.toString,
      "unsubscribedAt" -> subscriber.unsubscribedAt.map(_.toString),
      "status" -> (subscriber.status match {
        case repositories.Active => "active"
        case repositories.Unsubscribed => "unsubscribed"
      })
    )
  }

  def subscribe: Action[JsValue] = Action(parse.json) { implicit request =>
    (request.body \ "email").asOpt[String] match {
      case Some(email) =>
        Validator.validateEmail(email) match {
          case Right(validEmail) =>
            subscriberRepository.subscribe(validEmail) match {
              case Right(subscriber) =>
                val baseUrl = s"${request.host}/api/unsubscribe/"
                val protocol = if (request.secure) "https" else "http"
                val fullBaseUrl = s"$protocol://$baseUrl"
                emailService.sendWelcomeEmail(validEmail, subscriber.unsubscribeToken, fullBaseUrl) match {
                  case Right(_) =>
                    logger.info(s"User subscribed: $validEmail")
                  case Left(error) =>
                    logger.warn(s"Subscription email failed: $error")
                }
                Ok(Json.obj(
                  "status" -> "success",
                  "message" -> "Successfully subscribed",
                  "data" -> subscriberToJson(subscriber)
                ))
              case Left(error) =>
                Conflict(Json.obj(
                  "status" -> "error",
                  "message" -> error
                ))
            }
          case Left(error) =>
            BadRequest(Json.obj(
              "status" -> "error",
              "message" -> error
            ))
        }
      case None =>
        BadRequest(Json.obj(
          "status" -> "error",
          "message" -> "Email field is required"
        ))
    }
  }

  def unsubscribe: Action[JsValue] = Action(parse.json) { implicit request =>
    (request.body \ "email").asOpt[String] match {
      case Some(email) =>
        Validator.validateEmail(email) match {
          case Right(validEmail) =>
            subscriberRepository.unsubscribe(validEmail) match {
              case Right(subscriber) =>
                emailService.sendUnsubscribeEmail(validEmail) match {
                  case Right(_) =>
                    logger.info(s"User unsubscribed: $validEmail")
                  case Left(error) =>
                    logger.warn(s"Unsubscribe email failed: $error")
                }
                Ok(Json.obj(
                  "status" -> "success",
                  "message" -> "Successfully unsubscribed",
                  "data" -> subscriberToJson(subscriber)
                ))
              case Left(error) =>
                NotFound(Json.obj(
                  "status" -> "error",
                  "message" -> error
                ))
            }
          case Left(error) =>
            BadRequest(Json.obj(
              "status" -> "error",
              "message" -> error
            ))
        }
      case None =>
        BadRequest(Json.obj(
          "status" -> "error",
          "message" -> "Email field is required"
        ))
    }
  }

  def unsubscribeWithToken(token: String): Action[AnyContent] = Action { implicit request =>
    subscriberRepository.unsubscribeByToken(token) match {
      case Right(subscriber) =>
        emailService.sendUnsubscribeEmail(subscriber.email) match {
          case Right(_) =>
            logger.info(s"User unsubscribed via token: ${subscriber.email}")
          case Left(error) =>
            logger.warn(s"Token unsubscribe email failed: $error")
        }
        Ok(Json.obj(
          "status" -> "success",
          "message" -> "Successfully unsubscribed",
          "data" -> subscriberToJson(subscriber)
        ))
      case Left(error) =>
        NotFound(Json.obj(
          "status" -> "error",
          "message" -> error
        ))
    }
  }

  def getSubscriber(email: String): Action[AnyContent] = Action { implicit request =>
    Validator.validateEmail(email) match {
      case Right(validEmail) =>
        subscriberRepository.findByEmail(validEmail) match {
          case Some(subscriber) =>
            Ok(Json.obj(
              "status" -> "success",
              "data" -> subscriberToJson(subscriber)
            ))
          case None =>
            NotFound(Json.obj(
              "status" -> "error",
              "message" -> s"Subscriber not found: $validEmail"
            ))
        }
      case Left(error) =>
        BadRequest(Json.obj(
          "status" -> "error",
          "message" -> error
        ))
    }
  }

  def listSubscribers(status: Option[String]): Action[AnyContent] = Action { implicit request =>
    val subscribers = status match {
      case Some("active") => subscriberRepository.listActive()
      case Some("unsubscribed") => subscriberRepository.listUnsubscribed()
      case _ => subscriberRepository.listAll()
    }
    Ok(Json.obj(
      "status" -> "success",
      "count" -> subscribers.size,
      "data" -> JsArray(subscribers.map(s => Json.toJson(SubscriberRecord(s))))
    ))
  }

  def isSubscribed(email: String): Action[AnyContent] = Action { implicit request =>
    Validator.validateEmail(email) match {
      case Right(validEmail) =>
        Ok(Json.obj(
          "status" -> "success",
          "email" -> validEmail,
          "isSubscribed" -> subscriberRepository.isSubscribed(validEmail)
        ))
      case Left(error) =>
        BadRequest(Json.obj(
          "status" -> "error",
          "message" -> error
        ))
    }
  }

  def getStats: Action[AnyContent] = Action { implicit request =>
    Ok(Json.obj(
      "status" -> "success",
      "data" -> Json.obj(
        "total" -> subscriberRepository.countTotal(),
        "active" -> subscriberRepository.countActive(),
        "unsubscribed" -> subscriberRepository.countUnsubscribed(),
        "today" -> subscriberRepository.countToday(),
        "thisWeek" -> subscriberRepository.countThisWeek(),
        "retentionRate" -> (if (subscriberRepository.countTotal() > 0) {
          (subscriberRepository.countActive().toDouble / subscriberRepository.countTotal().toDouble) * 100
        } else 0.0)
      )
    ))
  }
}
