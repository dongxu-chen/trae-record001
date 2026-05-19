package com.payment.reconciliation.ddd.core;

public interface CommandHandler<C extends Command, R> {
    R handle(C command);
}
