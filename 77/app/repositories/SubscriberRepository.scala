package repositories

import javax.inject.Singleton
import java.util.concurrent.ConcurrentHashMap
import scala.jdk.CollectionConverters._
import java.security.MessageDigest
import java.time.format.DateTimeFormatter

sealed trait SubscriptionStatus
case object Active extends SubscriptionStatus
case object Unsubscribed extends SubscriptionStatus

case class Subscriber(
  email: String,
  unsubscribeToken: String,
  subscribedAt: java.time.LocalDateTime = java.time.LocalDateTime.now(),
  unsubscribedAt: Option[java.time.LocalDateTime] = None,
  status: SubscriptionStatus = Active
)

case class SubscriberRecord(
  email: String,
  unsubscribeToken: String,
  subscribedAt: String,
  unsubscribedAt: Option[String],
  status: String
)

object SubscriberRecord {
  private val formatter = DateTimeFormatter.ISO_LOCAL_DATE_TIME

  def apply(subscriber: Subscriber): SubscriberRecord = {
    SubscriberRecord(
      email = subscriber.email,
      unsubscribeToken = subscriber.unsubscribeToken,
      subscribedAt = subscriber.subscribedAt.format(formatter),
      unsubscribedAt = subscriber.unsubscribedAt.map(_.format(formatter)),
      status = subscriber.status match {
        case Active => "active"
        case Unsubscribed => "unsubscribed"
      }
    )
  }
}

@Singleton
class SubscriberRepository {
  private val subscribers = new ConcurrentHashMap[String, Subscriber]()
  private val tokenToEmail = new ConcurrentHashMap[String, String]()

  private def generateUnsubscribeToken(email: String): String = {
    val timestamp = java.time.LocalDateTime.now().toString
    val input = s"$email-$timestamp-${Math.random()}"
    val digest = MessageDigest.getInstance("SHA-256")
    val hashBytes = digest.digest(input.getBytes("UTF-8"))
    hashBytes.map("%02x".format(_)).mkString
  }

  def subscribe(email: String): Either[String, Subscriber] = {
    subscribers.get(email) match {
      case existing if existing != null && existing.status == Active =>
        Left(s"Email $email is already subscribed")
      case existing if existing != null && existing.status == Unsubscribed =>
        val reactivated = existing.copy(
          status = Active,
          unsubscribedAt = None
        )
        subscribers.put(email, reactivated)
        Right(reactivated)
      case _ =>
        val token = generateUnsubscribeToken(email)
        val newSubscriber = Subscriber(email, token)
        subscribers.put(email, newSubscriber)
        tokenToEmail.put(token, email)
        Right(newSubscriber)
    }
  }

  def unsubscribe(email: String): Either[String, Subscriber] = {
    subscribers.get(email) match {
      case null =>
        Left(s"Email $email is not subscribed")
      case subscriber if subscriber.status == Unsubscribed =>
        Left(s"Email $email is already unsubscribed")
      case subscriber =>
        val updated = subscriber.copy(
          status = Unsubscribed,
          unsubscribedAt = Some(java.time.LocalDateTime.now())
        )
        subscribers.put(email, updated)
        Right(updated)
    }
  }

  def unsubscribeByToken(token: String): Either[String, Subscriber] = {
    tokenToEmail.get(token) match {
      case null =>
        Left("Invalid or expired unsubscribe token")
      case email =>
        unsubscribe(email)
    }
  }

  def getByToken(token: String): Option[Subscriber] = {
    Option(tokenToEmail.get(token)).flatMap(email => Option(subscribers.get(email)))
  }

  def isSubscribed(email: String): Boolean = {
    subscribers.get(email) match {
      case null => false
      case s => s.status == Active
    }
  }

  def findByEmail(email: String): Option[Subscriber] = {
    Option(subscribers.get(email))
  }

  def listAll(): List[Subscriber] = {
    subscribers.values().asScala.toList
  }

  def listActive(): List[Subscriber] = {
    subscribers.values().asScala.filter(_.status == Active).toList
  }

  def listUnsubscribed(): List[Subscriber] = {
    subscribers.values().asScala.filter(_.status == Unsubscribed).toList
  }

  def countActive(): Long = {
    listActive().size
  }

  def countUnsubscribed(): Long = {
    listUnsubscribed().size
  }

  def countTotal(): Long = {
    subscribers.size()
  }

  def countToday(): Long = {
    val today = java.time.LocalDate.now()
    subscribers.values().asScala.count(s => s.subscribedAt.toLocalDate.isEqual(today))
  }

  def countThisWeek(): Long = {
    val weekAgo = java.time.LocalDate.now().minusDays(7)
    subscribers.values().asScala.count(s => s.subscribedAt.toLocalDate.isAfter(weekAgo))
  }
}
