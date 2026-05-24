package com.wolfkill.netty;

import io.netty.bootstrap.ServerBootstrap;
import io.netty.channel.ChannelFuture;
import io.netty.channel.ChannelInitializer;
import io.netty.channel.ChannelOption;
import io.netty.channel.EventLoopGroup;
import io.netty.channel.nio.NioEventLoopGroup;
import io.netty.channel.socket.SocketChannel;
import io.netty.channel.socket.nio.NioServerSocketChannel;
import io.netty.handler.codec.protobuf.ProtobufDecoder;
import io.netty.handler.codec.protobuf.ProtobufEncoder;
import io.netty.handler.codec.protobuf.ProtobufVarint32FrameDecoder;
import io.netty.handler.codec.protobuf.ProtobufVarint32LengthFieldPrepender;
import io.netty.handler.timeout.IdleStateHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;

@Component
public class NettyServer {

    private static final Logger logger = LoggerFactory.getLogger(NettyServer.class);

    @Value("${netty.port:9000}")
    private int port;

    @Value("${netty.boss-threads:2}")
    private int bossThreads;

    @Value("${netty.worker-threads:8}")
    private int workerThreads;

    @Value("${netty.reader-idle-time:60}")
    private int readerIdleTime;

    @Value("${netty.writer-idle-time:30}")
    private int writerIdleTime;

    @Value("${netty.all-idle-time:0}")
    private int allIdleTime;

    private final MessageHandler messageHandler;

    private EventLoopGroup bossGroup;
    private EventLoopGroup workerGroup;

    public NettyServer(MessageHandler messageHandler) {
        this.messageHandler = messageHandler;
    }

    public void start() throws InterruptedException {
        bossGroup = new NioEventLoopGroup(bossThreads);
        workerGroup = new NioEventLoopGroup(workerThreads);

        try {
            ServerBootstrap bootstrap = new ServerBootstrap();
            bootstrap.group(bossGroup, workerGroup)
                    .channel(NioServerSocketChannel.class)
                    .option(ChannelOption.SO_BACKLOG, 1024)
                    .childOption(ChannelOption.SO_KEEPALIVE, true)
                    .childOption(ChannelOption.TCP_NODELAY, true)
                    .childHandler(new ChannelInitializer<SocketChannel>() {
                        @Override
                        protected void initChannel(SocketChannel ch) {
                            ch.pipeline().addLast(
                                    new IdleStateHandler(readerIdleTime, writerIdleTime, allIdleTime, TimeUnit.SECONDS),
                                    new ProtobufVarint32FrameDecoder(),
                                    new ProtobufDecoder(com.wolfkill.protocol.MessageWrapper.getDefaultInstance()),
                                    new ProtobufVarint32LengthFieldPrepender(),
                                    new ProtobufEncoder(),
                                    new ConnectionHandler(messageHandler),
                                    messageHandler
                            );
                        }
                    });

            ChannelFuture future = bootstrap.bind(port).sync();
            logger.info("Netty server started on port: {}", port);

            future.channel().closeFuture().sync();
        } finally {
            shutdown();
        }
    }

    public void shutdown() {
        if (bossGroup != null && !bossGroup.isShuttingDown()) {
            bossGroup.shutdownGracefully();
        }
        if (workerGroup != null && !workerGroup.isShuttingDown()) {
            workerGroup.shutdownGracefully();
        }
        logger.info("Netty server shutdown");
    }
}
