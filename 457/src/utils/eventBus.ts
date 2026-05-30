export type EventType =
  | 'PIVOT_CONFIG_CHANGED'
  | 'PIVOT_DATA_UPDATED'
  | 'CELL_CLICKED'
  | 'DRILLDOWN_REQUESTED'
  | 'DRILLDOWN_DATA_READY'
  | 'CHART_TYPE_CHANGED'
  | 'DATA_UPLOADED'
  | 'EXPORT_REQUESTED';

export interface EventPayload {
  PIVOT_CONFIG_CHANGED: {
    rows: string[];
    cols: string[];
    values: { field: string; aggregation: string }[];
  };
  PIVOT_DATA_UPDATED: {
    pivotResult: any;
  };
  CELL_CLICKED: {
    rowFilters: Record<string, string>;
    colFilters: Record<string, string>;
    valueField: string;
    value: number;
  };
  DRILLDOWN_REQUESTED: {
    rowFilters: Record<string, string>;
    colFilters: Record<string, string>;
    valueField: string;
  };
  DRILLDOWN_DATA_READY: {
    data: any[];
    rowFilters: Record<string, string>;
    colFilters: Record<string, string>;
    valueField: string;
  };
  CHART_TYPE_CHANGED: {
    chartType: 'bar' | 'line' | 'pie';
  };
  DATA_UPLOADED: {
    data: any[];
  };
  EXPORT_REQUESTED: {
    type: 'pivot' | 'drilldown';
  };
}

type EventCallback<T extends EventType> = (
  payload: EventPayload[T],
  eventType: T
) => void;

class EventBus {
  private listeners: Map<EventType, Set<EventCallback<any>>> = new Map();
  private history: Map<EventType, any> = new Map();
  private debug: boolean = false;

  enableDebug(enable: boolean = true) {
    this.debug = enable;
  }

  on<T extends EventType>(
    eventType: T,
    callback: EventCallback<T>
  ): () => void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType)!.add(callback);

    if (this.history.has(eventType)) {
      callback(this.history.get(eventType), eventType);
    }

    return () => {
      this.off(eventType, callback);
    };
  }

  off<T extends EventType>(eventType: T, callback: EventCallback<T>) {
    this.listeners.get(eventType)?.delete(callback);
  }

  emit<T extends EventType>(eventType: T, payload: EventPayload[T]) {
    if (this.debug) {
      console.log(`[EventBus] ${eventType}`, payload);
    }

    this.history.set(eventType, payload);

    const callbacks = this.listeners.get(eventType);
    if (callbacks) {
      callbacks.forEach((cb) => {
        try {
          cb(payload, eventType);
        } catch (error) {
          console.error(`[EventBus] Error in listener for ${eventType}:`, error);
        }
      });
    }
  }

  getLastEvent<T extends EventType>(eventType: T): EventPayload[T] | undefined {
    return this.history.get(eventType);
  }

  clearHistory(eventType?: EventType) {
    if (eventType) {
      this.history.delete(eventType);
    } else {
      this.history.clear();
    }
  }

  clearAll() {
    this.listeners.clear();
    this.history.clear();
  }
}

export const eventBus = new EventBus();

export const useEventBus = () => {
  return {
    on: eventBus.on.bind(eventBus),
    off: eventBus.off.bind(eventBus),
    emit: eventBus.emit.bind(eventBus),
    getLastEvent: eventBus.getLastEvent.bind(eventBus),
  };
};
