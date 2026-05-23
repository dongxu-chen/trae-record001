package com.emailmarketing.service;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.emailmarketing.entity.EmailSendLog;
import com.emailmarketing.mapper.EmailSendLogMapper;
import org.springframework.stereotype.Service;

@Service
public class EmailSendLogService extends ServiceImpl<EmailSendLogMapper, EmailSendLog> {
}
