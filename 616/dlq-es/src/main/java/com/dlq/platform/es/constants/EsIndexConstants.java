package com.dlq.platform.es.constants;

public class EsIndexConstants {

    public static final String INDEX_DEAD_LETTER = "dlq_dead_letter";

    public static final String INDEX_ARCHIVE_PREFIX = "dlq_archive_";

    public static final String FIELD_ID = "id";
    public static final String FIELD_MQ_TYPE = "mqType";
    public static final String FIELD_TOPIC = "topic";
    public static final String FIELD_QUEUE_NAME = "queueName";
    public static final String FIELD_MESSAGE_ID = "messageId";
    public static final String FIELD_MESSAGE_BODY = "messageBody";
    public static final String FIELD_HEADERS = "headers";
    public static final String FIELD_DEAD_REASON = "deadReason";
    public static final String FIELD_DEAD_REASON_TYPE = "deadReasonType";
    public static final String FIELD_STACK_TRACE = "stackTrace";
    public static final String FIELD_ORIGINAL_TOPIC = "originalTopic";
    public static final String FIELD_ORIGINAL_QUEUE = "originalQueue";
    public static final String FIELD_RETRY_COUNT = "retryCount";
    public static final String FIELD_PROCESS_STATUS = "processStatus";
    public static final String FIELD_CREATE_TIME = "createTime";
    public static final String FIELD_UPDATE_TIME = "updateTime";

    public static final String ANALYZER_IK_MAX_WORD = "ik_max_word";
    public static final String ANALYZER_IK_SMART = "ik_smart";

    public static String getArchiveIndex(String suffix) {
        return INDEX_ARCHIVE_PREFIX + suffix;
    }
}
