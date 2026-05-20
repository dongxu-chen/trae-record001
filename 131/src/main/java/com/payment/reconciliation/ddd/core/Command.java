package com.payment.reconciliation.ddd.core;

import java.time.LocalDateTime;

public abstract class Command {
    private String commandId;
    private LocalDateTime issuedAt;

    public Command() {
        this.issuedAt = LocalDateTime.now();
    }

    public String getCommandId() {
        return commandId;
    }

    public void setCommandId(String commandId) {
        this.commandId = commandId;
    }

    public LocalDateTime getIssuedAt() {
        return issuedAt;
    }

    public void setIssuedAt(LocalDateTime issuedAt) {
        this.issuedAt = issuedAt;
    }
}
