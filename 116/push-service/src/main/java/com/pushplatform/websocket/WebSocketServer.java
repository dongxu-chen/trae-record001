package com.pushplatform.websocket;

import io.netty.bootstrap.ServerBootstrap;
import io.netty.channel.ChannelFuture;
import io.netty.channel.ChannelInitializer;
import io.netty.channel.EventLoopGroup;
import io.netty.channel.nio.NioEventLoopGroup;
import io.netty.channel.socket.SocketChannel;
import io.netty.channel.socket.nio.NioServerSocketChannel;
import io.netty.handler.codec.http.HttpObjectAggregator;
import io.netty.handler.codec.http.HttpServerCodec;
import io.netty.handler.codec.http.websocketx.WebSocketServerProtocolHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import javax.annotation.PreDestroy;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Component
public class WebSocketServer implements CommandLineRunner {

    private static final Logger logger = LoggerFactory.getLogger(WebSocketServer.class);

    @Value("${push.websocket.port:9000}")
    private int port;

    @Value("${push.websocket.boss-threads:1}")
    private int bossThreads;

    @Value("${push.websocket.worker-threads:8}")
    private int workerThreads;

    @Value("${push.websocket.business-threads:20}")
    private int businessThreads;

    private EventLoopGroup bossGroup;
    private EventLoopGroup workerGroup;
    private ExecutorService businessExecutor;

    @Autowired
    private WebSocketHandler webSocketHandler;

    @Override
    public void run(String... args) throws Exception {
        start();
    }

    public void start() {
        bossGroup = new NioEventLoopGroup(bossThreads);
        workerGroup = new NioEventLoopGroup(workerThreads);
        businessExecutor = Executors.newFixedThreadPool(businessThreads, 
                r -> new Thread(r, "ws-business-" + System.currentTimeMillis()));

        webSocketHandler.setBusinessExecutor(businessExecutor);

        try {
            ServerBootstrap bootstrap = new ServerBootstrap();
            bootstrap.group(bossGroup, workerGroup)
                    .channel(NioServerSocketChannel.class)
                    .childHandler(new ChannelInitializer<SocketChannel>() {
                        @Override
                        protected void initChannel(SocketChannel ch) {
                            ch.pipeline()
                                    .addLast("http-codec", new HttpServerCodec())
                                    .addLast("aggregator", new HttpObjectAggregator(65536))
                                    .addLast("ws-protocol", new WebSocketServerProtocolHandler("/ws"))
                                    .addLast("ws-handler", webSocketHandler);
                        }
                    });

            ChannelFuture future = bootstrap.bind(port).sync();
            logger.info("WebSocket Server started on port: {}, bossThreads: {}, workerThreads: {}, businessThreads: {}",
                    port, bossThreads, workerThreads, businessThreads);
            future.channel().closeFuture().addListener(f -> {
                logger.info("WebSocket Server closed");
            });
        } catch (Exception e) {
            logger.error("WebSocket Server start failed", e);
        }
    }

    @PreDestroy
    public void stop() {
        if (bossGroup != null) {
            bossGroup.shutdownGracefully();
        }
        if (workerGroup != null) {
            workerGroup.shutdownGracefully();
        }
        if (businessExecutor != null) {
            businessExecutor.shutdown();
        }
        logger.info("WebSocket Server stopped");
    }

    public ExecutorService getBusinessExecutor() {
        return businessExecutor;
    }
}
