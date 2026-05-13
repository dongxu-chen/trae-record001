package jobs

import javax.inject._
import play.api.inject.ApplicationLifecycle
import play.api.{Configuration, Logger}
import repositories.SubscriberRepository
import scala.concurrent.{ExecutionContext, Future}
import scala.concurrent.duration._
import java.util.concurrent.atomic.AtomicReference
import java.time.LocalDateTime

case class StatsSnapshot(
  timestamp: LocalDateTime,
  total: Long,
  active: Long,
  unsubscribed: Long,
  today: Long,
  thisWeek: Long,
  retentionRate: Double
)

@Singleton
class StatsJob @Inject()(
  subscriberRepository: SubscriberRepository,
  lifecycle: ApplicationLifecycle,
  configuration: Configuration
)(implicit ec: ExecutionContext) {

  private val logger = Logger(this.getClass)

  private val latestSnapshot = new AtomicReference[Option[StatsSnapshot]](None)
  private val history = new AtomicReference[List[StatsSnapshot]](Nil)

  private val intervalMinutes = configuration.getOptional[Int]("stats.job.intervalMinutes").getOrElse(5)
  private val maxHistorySize = configuration.getOptional[Int]("stats.job.maxHistorySize").getOrElse(100)

  private var scheduler: Option[java.util.concurrent.ScheduledExecutorService] = None

  def currentSnapshot: Option[StatsSnapshot] = latestSnapshot.get()

  def getHistory: List[StatsSnapshot] = history.get()

  private def generateSnapshot(): StatsSnapshot = {
    val total = subscriberRepository.countTotal()
    val active = subscriberRepository.countActive()
    val unsubscribed = subscriberRepository.countUnsubscribed()
    val retentionRate = if (total > 0) (active.toDouble / total.toDouble) * 100 else 0.0

    StatsSnapshot(
      timestamp = LocalDateTime.now(),
      total = total,
      active = active,
      unsubscribed = unsubscribed,
      today = subscriberRepository.countToday(),
      thisWeek = subscriberRepository.countThisWeek(),
      retentionRate = retentionRate
    )
  }

  private def runJob(): Unit = {
    try {
      val snapshot = generateSnapshot()
      latestSnapshot.set(Some(snapshot))
      history.updateAndGet(prev => (snapshot :: prev).take(maxHistorySize))

      logger.info(s"Stats snapshot generated at ${snapshot.timestamp}: " +
        s"total=${snapshot.total}, active=${snapshot.active}, " +
        s"unsubscribed=${snapshot.unsubscribed}, retention=${snapshot.retentionRate}%.2f%%")

    } catch {
      case e: Exception =>
        logger.error(s"Stats job failed: ${e.getMessage}", e)
    }
  }

  private def start(): Unit = {
    runJob()

    val executor = java.util.concurrent.Executors.newSingleThreadScheduledExecutor()
    executor.scheduleAtFixedRate(
      () => runJob(),
      intervalMinutes,
      intervalMinutes,
      java.util.concurrent.TimeUnit.MINUTES
    )
    scheduler = Some(executor)

    logger.info(s"Stats job started with interval of $intervalMinutes minutes")
  }

  def stop(): Unit = {
    scheduler.foreach(_.shutdown())
    logger.info("Stats job stopped")
  }

  def forceRun(): StatsSnapshot = {
    runJob()
    latestSnapshot.get().getOrElse(generateSnapshot())
  }

  start()

  lifecycle.addStopHook(() => Future {
    stop()
  })
}
