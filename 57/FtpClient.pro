QT += core gui network

greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

CONFIG += c++11

TARGET = FtpClient
TEMPLATE = app

SOURCES += \
    main.cpp \
    mainwindow.cpp \
    ftp_connection.cpp \
    transfer_thread.cpp \
    local_browser.cpp \
    site_manager.cpp \
    log_widget.cpp

HEADERS += \
    mainwindow.h \
    ftp_connection.h \
    transfer_thread.h \
    local_browser.h \
    site_manager.h \
    log_widget.h

FORMS += \
    mainwindow.ui
