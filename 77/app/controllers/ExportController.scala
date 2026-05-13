package controllers

import javax.inject._
import play.api.mvc._
import play.api.libs.json._
import repositories.SubscriberRepository
import jobs.StatsJob
import java.time.format.DateTimeFormatter
import java.time.LocalDateTime
import java.time.ZoneId

@Singleton
class ExportController @Inject()(
  val controllerComponents: ControllerComponents,
  subscriberRepository: SubscriberRepository,
  statsJob: StatsJob
) extends BaseController {

  private val dateFormatter = DateTimeFormatter.ISO_LOCAL_DATE_TIME

  private def escapeCsv(value: String): String = {
    val escaped = value.replace("\"", "\"\"")
    if (escaped.contains(",") || escaped.contains("\"") || escaped.contains("\n")) {
      s""""$escaped""""
    } else {
      escaped
    }
  }

  private def subscriberToCsvLine(subscriber: repositories.Subscriber): String = {
    val status = subscriber.status match {
      case repositories.Active => "active"
      case repositories.Unsubscribed => "unsubscribed"
    }
    val unsubscribedAt = subscriber.unsubscribedAt.map(_.format(dateFormatter)).getOrElse("")
    s"${escapeCsv(subscriber.email)},${escapeCsv(subscriber.unsubscribeToken)},${subscriber.subscribedAt.format(dateFormatter)},${unsubscribedAt},$status"
  }

  def exportSubscribers(status: Option[String]): Action[AnyContent] = Action { implicit request =>
    val subscribers = status match {
      case Some("active") => subscriberRepository.listActive()
      case Some("unsubscribed") => subscriberRepository.listUnsubscribed()
      case _ => subscriberRepository.listAll()
    }

    val header = "email,unsubscribe_token,subscribed_at,unsubscribed_at,status"
    val lines = header +: subscribers.map(subscriberToCsvLine)
    val csvContent = lines.mkString("\n")

    val timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"))
    val filename = status match {
      case Some(s) => s"subscribers_${s}_$timestamp.csv"
      case None => s"subscribers_$timestamp.csv"
    }

    Ok(csvContent)
      .as("text/csv; charset=utf-8")
      .withHeaders(
        "Content-Disposition" -> s"""attachment; filename="$filename""")
  }

  def exportStats: Action[AnyContent] = Action { implicit request =>
    val history = statsJob.getHistory

    val header = "timestamp,total,active,unsubscribed,today,this_week,retention_rate"
    val lines = header +: history.map { snapshot =>
      s"${snapshot.timestamp.format(dateFormatter)},${snapshot.total},${snapshot.active},${snapshot.unsubscribed},${snapshot.today},${snapshot.thisWeek},${snapshot.retentionRate}"
    }
    val csvContent = lines.mkString("\n")

    val timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"))
    val filename = s"stats_history_$timestamp.csv"

    Ok(csvContent)
      .as("text/csv; charset=utf-8")
      .withHeaders(
        "Content-Disposition" -> s"""attachment; filename="$filename"""")
  }

  def exportStatsJson: Action[AnyContent] = Action { implicit request =>
    val latest = statsJob.currentSnapshot
    val history = statsJob.getHistory

    implicit val snapshotWrites: Writes[jobs.StatsSnapshot] = Json.writes[jobs.StatsSnapshot]

    Ok(Json.obj(
      "status" -> "success",
      "data" -> Json.obj(
        "latest" -> latest.map(s => Json.toJson(s)),
        "historyCount" -> history.size,
        "history" -> JsArray(history.map(Json.toJson(_)))
      )
    ))
  }

  def forceStatsSnapshot: Action[AnyContent] = Action { implicit request =>
    val snapshot = statsJob.forceRun()

    implicit val snapshotWrites: Writes[jobs.StatsSnapshot] = Json.writes[jobs.StatsSnapshot]

    Ok(Json.obj(
      "status" -> "success",
      "message" -> "Stats snapshot generated",
      "data" -> Json.toJson(snapshot)
    ))
  }
}
