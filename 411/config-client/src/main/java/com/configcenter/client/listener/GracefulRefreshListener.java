package com.configcenter.client.listener;

import com.configcenter.client.config.GracefulRefreshHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cloud.bus.event.RefreshRemoteApplicationEvent;
import org.springframework.cloud.context.scope.refresh.RefreshScopeRefreshedEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Component
public class GracefulRefreshListener {

    private static final Logger logger = LoggerFactory.getLogger(GracefulRefreshListener.class);

    private final GracefulRefreshHandler gracefulRefreshHandler;

    public GracefulRefreshListener(GracefulRefreshHandler gracefulRefreshHandler) {
        this.gracefulRefreshHandler = gracefulRefreshHandler;
    }

    @EventListener
    public void onBusRefreshEvent(RefreshRemoteApplicationEvent event) {
        logger.info("收到Bus刷新事件，触发优雅刷新: destination={}, originService={}",
                event.getDestinationService(), event.getOriginService());
        gracefulRefreshHandler.triggerGracefulRefresh();
    }

    @EventListener
    public void onRefreshComplete(RefreshScopeRefreshedEvent event) {
        logger.info("配置刷新完成，RefreshScope已更新");
    }
}
