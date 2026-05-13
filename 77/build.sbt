name := """mail-subscription-api"""
organization := "com.example"

version := "1.0.0"

lazy val root = (project in file(".")).enablePlugins(PlayScala)

scalaVersion := "2.13.12"

libraryDependencies ++= Seq(
  guice,
  "org.scalatestplus.play" %% "scalatestplus-play" % "7.0.0" % Test,
  "com.typesafe.play" %% "play-mailer" % "9.0.0",
  "com.typesafe.play" %% "play-mailer-guice" % "9.0.0"
)
