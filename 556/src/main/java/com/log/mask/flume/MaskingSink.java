package com.log.mask.flume;

import com.log.mask.config.MaskConfig;
import com.log.mask.parser.LogParser;
import com.log.mask.parser.LogParserFactory;
import com.log.mask.rule.RuleEngine;
import org.apache.flume.*;
import org.apache.flume.conf.Configurable;
import org.apache.flume.sink.AbstractSink;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;

public class MaskingSink extends AbstractSink implements Configurable {
    private static final Logger logger = LoggerFactory.getLogger(MaskingSink.class);
    
    private RuleEngine ruleEngine;
    private LogParser logParser;
    private String logFormat;
    private String configFile;

    @Override
    public void configure(Context context) {
        logFormat = context.getString("log.format", "text");
        configFile = context.getString("config.file", "mask-config.properties");
        
        ruleEngine = new RuleEngine();
        logParser = LogParserFactory.getParser(logFormat);
        
        try {
            MaskConfig config = new MaskConfig();
            config.loadFromFile(configFile);
            
            if (!config.isEnableDefaultRules()) {
                ruleEngine.clearAllRules();
            }
            ruleEngine.addRules(config.getCustomRules());
            
            if (config.getLogFormat() != null) {
                logParser = LogParserFactory.getParser(config.getLogFormat());
            }
            
            logger.info("MaskingSink configured with format: {}", logFormat);
        } catch (IOException e) {
            logger.warn("Could not load config file, using default rules: {}", e.getMessage());
        }
    }

    @Override
    public void start() {
        logger.info("MaskingSink starting...");
        super.start();
        logger.info("MaskingSink started");
    }

    @Override
    public void stop() {
        logger.info("MaskingSink stopping...");
        super.stop();
        logger.info("MaskingSink stopped");
    }

    @Override
    public Status process() throws EventDeliveryException {
        Status status = Status.READY;
        Channel channel = getChannel();
        Transaction txn = channel.getTransaction();
        
        try {
            txn.begin();
            Event event = channel.take();
            
            if (event == null) {
                status = Status.BACKOFF;
                txn.commit();
                return status;
            }
            
            byte[] body = event.getBody();
            String originalLog = new String(body);
            
            String maskedLog = logParser.parseAndMask(originalLog, ruleEngine.getMaskEngine());
            
            event.setBody(maskedLog.getBytes());
            
            logger.debug("Original: {} -> Masked: {}", originalLog, maskedLog);
            
            txn.commit();
        } catch (Throwable t) {
            txn.rollback();
            logger.error("Error processing event", t);
            if (t instanceof Error) {
                throw (Error) t;
            }
            throw new EventDeliveryException("Failed to process event", t);
        } finally {
            txn.close();
        }
        
        return status;
    }
}
