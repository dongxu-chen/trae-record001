package com.log.collector.sink;

import org.apache.flume.*;
import org.apache.flume.conf.Configurable;
import org.apache.flume.sink.AbstractSink;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.FSDataOutputStream;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.net.URI;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.atomic.AtomicLong;

public class HDFSSink extends AbstractSink implements Configurable {

    private static final Logger logger = LoggerFactory.getLogger(HDFSSink.class);

    private String hdfsUri;
    private String basePath;
    private String filePrefix;
    private String fileSuffix;
    private long rollInterval;
    private long rollSize;
    private int rollCount;
    private int batchSize;
    private boolean useCompression;
    private String compressionCodec;

    private FileSystem fileSystem;
    private FSDataOutputStream outputStream;
    private Path currentFilePath;
    private AtomicLong eventCount;
    private long lastRollTime;
    private SimpleDateFormat dateFormat;

    @Override
    public void configure(Context context) {
        hdfsUri = context.getString("hdfsUri", "hdfs://localhost:9000");
        basePath = context.getString("path", "/flume/logs");
        filePrefix = context.getString("filePrefix", "log-");
        fileSuffix = context.getString("fileSuffix", ".log");
        rollInterval = context.getLong("rollInterval", 300);
        rollSize = context.getLong("rollSize", 134217728);
        rollCount = context.getInteger("rollCount", 10000);
        batchSize = context.getInteger("batchSize", 1000);
        useCompression = context.getBoolean("useCompression", false);
        compressionCodec = context.getString("compressionCodec", "gzip");

        dateFormat = new SimpleDateFormat("yyyy-MM-dd/HH");
        dateFormat.setTimeZone(TimeZone.getTimeZone("UTC"));

        logger.info("HDFSSink configured - uri: {}, path: {}, rollInterval: {}s",
                hdfsUri, basePath, rollInterval);
    }

    @Override
    public synchronized void start() {
        logger.info("Starting HDFSSink...");
        try {
            Configuration conf = new Configuration();
            conf.set("fs.defaultFS", hdfsUri);
            conf.set("dfs.replication", "3");
            conf.set("dfs.support.append", "true");

            fileSystem = FileSystem.get(new URI(hdfsUri), conf);
            eventCount = new AtomicLong(0);
            lastRollTime = System.currentTimeMillis();

            logger.info("HDFSSink started successfully");
        } catch (Exception e) {
            logger.error("Failed to start HDFSSink", e);
            throw new FlumeException("Failed to connect to HDFS", e);
        }
        super.start();
    }

    @Override
    public Status process() throws EventDeliveryException {
        Channel channel = getChannel();
        Transaction transaction = channel.getTransaction();
        List<Event> events = new ArrayList<>();

        try {
            transaction.begin();

            for (int i = 0; i < batchSize; i++) {
                Event event = channel.take();
                if (event == null) {
                    break;
                }
                events.add(event);
            }

            if (events.isEmpty()) {
                transaction.commit();
                return Status.BACKOFF;
            }

            writeEvents(events);

            transaction.commit();
            logger.debug("Successfully wrote {} events to HDFS", events.size());
            return Status.READY;

        } catch (Exception e) {
            transaction.rollback();
            logger.error("Failed to process events", e);
            sendToDeadLetterQueue(events, e);
            throw new EventDeliveryException("Failed to write to HDFS", e);
        } finally {
            transaction.close();
        }
    }

    private void writeEvents(List<Event> events) throws IOException {
        if (shouldRoll()) {
            rollFile();
        }

        if (outputStream == null) {
            createNewFile();
        }

        for (Event event : events) {
            outputStream.write(event.getBody());
            outputStream.write('\n');
            eventCount.incrementAndGet();
        }

        outputStream.hflush();
    }

    private boolean shouldRoll() {
        if (outputStream == null) {
            return true;
        }

        long currentTime = System.currentTimeMillis();
        long timeSinceRoll = (currentTime - lastRollTime) / 1000;

        if (rollInterval > 0 && timeSinceRoll >= rollInterval) {
            logger.debug("Rolling file due to time interval");
            return true;
        }

        if (rollSize > 0) {
            try {
                if (outputStream.getPos() >= rollSize) {
                    logger.debug("Rolling file due to size");
                    return true;
                }
            } catch (IOException e) {
                logger.warn("Failed to get file position", e);
            }
        }

        if (rollCount > 0 && eventCount.get() >= rollCount) {
            logger.debug("Rolling file due to event count");
            return true;
        }

        return false;
    }

    private void rollFile() throws IOException {
        if (outputStream != null) {
            try {
                outputStream.hflush();
                outputStream.close();
                logger.info("Closed file: {}", currentFilePath);
            } catch (IOException e) {
                logger.warn("Error closing file", e);
            }
            outputStream = null;
        }
    }

    private void createNewFile() throws IOException {
        String dateDir = dateFormat.format(new Date());
        Path dirPath = new Path(basePath + "/" + dateDir);

        if (!fileSystem.exists(dirPath)) {
            fileSystem.mkdirs(dirPath);
        }

        String fileName = filePrefix + System.currentTimeMillis() + fileSuffix;
        currentFilePath = new Path(dirPath, fileName);

        outputStream = fileSystem.create(currentFilePath, true);
        eventCount.set(0);
        lastRollTime = System.currentTimeMillis();

        logger.info("Created new HDFS file: {}", currentFilePath);
    }

    private void sendToDeadLetterQueue(List<Event> events, Exception e) {
        for (Event event : events) {
            event.getHeaders().put("dlq_reason", e.getMessage());
            event.getHeaders().put("dlq_timestamp", String.valueOf(System.currentTimeMillis()));
            event.getHeaders().put("dlq_sink", "hdfs");
        }
    }

    @Override
    public synchronized void stop() {
        logger.info("Stopping HDFSSink...");
        try {
            if (outputStream != null) {
                outputStream.hflush();
                outputStream.close();
            }
            if (fileSystem != null) {
                fileSystem.close();
            }
        } catch (IOException e) {
            logger.warn("Error closing HDFS resources", e);
        }
        logger.info("HDFSSink stopped");
        super.stop();
    }
}
