package api

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"strconv"
	"time"

	"github.com/gorilla/mux"

	"redis-cluster-scaler/internal/backup"
	"redis-cluster-scaler/internal/cluster"
	"redis-cluster-scaler/internal/cost"
	"redis-cluster-scaler/internal/failover"
	"redis-cluster-scaler/internal/migration"
	"redis-cluster-scaler/internal/monitor"
	"redis-cluster-scaler/internal/scaler"
	"redis-cluster-scaler/internal/simulation"
)

type Server struct {
	addr         string
	clusterMgr   *cluster.Manager
	monitor      *monitor.Monitor
	scaler       *scaler.Scaler
	migrator     *migration.Migrator
	backupMgr    *backup.BackupManager
	failoverMgr  *failover.FailoverManager
	costMgr      *cost.CostManager
	simulationMgr *simulation.SimulationManager
	router       *mux.Router
}

func New(
	addr string,
	clusterMgr *cluster.Manager,
	mon *monitor.Monitor,
	sc *scaler.Scaler,
	mig *migration.Migrator,
	bak *backup.BackupManager,
	failover *failover.FailoverManager,
	costMgr *cost.CostManager,
	simMgr *simulation.SimulationManager,
) *Server {
	s := &Server{
		addr:         addr,
		clusterMgr:   clusterMgr,
		monitor:      mon,
		scaler:       sc,
		migrator:     mig,
		backupMgr:    bak,
		failoverMgr:  failover,
		costMgr:      costMgr,
		simulationMgr: simMgr,
		router:       mux.NewRouter(),
	}
	s.setupRoutes()
	return s
}

func (s *Server) setupRoutes() {
	api := s.router.PathPrefix("/api/v1").Subrouter()
	api.Use(corsMiddleware)

	api.HandleFunc("/cluster/info", s.handleClusterInfo).Methods("GET")
	api.HandleFunc("/cluster/nodes", s.handleClusterNodes).Methods("GET")
	api.HandleFunc("/cluster/stats", s.handleClusterStats).Methods("GET")
	api.HandleFunc("/cluster/slots", s.handleSlotDistribution).Methods("GET")

	api.HandleFunc("/monitor/current", s.handleMonitorCurrent).Methods("GET")
	api.HandleFunc("/monitor/history", s.handleMonitorHistory).Methods("GET")
	api.HandleFunc("/monitor/range", s.handleMonitorRange).Methods("GET")

	api.HandleFunc("/scaler/events", s.handleScalerEvents).Methods("GET")
	api.HandleFunc("/scaler/add-node", s.handleScalerAddNode).Methods("POST")
	api.HandleFunc("/scaler/remove-node", s.handleScalerRemoveNode).Methods("POST")

	api.HandleFunc("/migration/plan", s.handleMigrationPlan).Methods("GET")
	api.HandleFunc("/migration/execute", s.handleMigrationExecute).Methods("POST")
	api.HandleFunc("/migration/evacuate/{nodeId}", s.handleMigrationEvacuate).Methods("POST")
	api.HandleFunc("/migration/migrate", s.handleMigrationMigrate).Methods("POST")
	api.HandleFunc("/migration/tasks", s.handleMigrationTasks).Methods("GET")
	api.HandleFunc("/migration/cancel/{taskId}", s.handleMigrationCancel).Methods("POST")

	api.HandleFunc("/backup/list", s.handleBackupList).Methods("GET")
	api.HandleFunc("/backup/create", s.handleBackupCreate).Methods("POST")

	api.HandleFunc("/failover/health", s.handleFailoverHealth).Methods("GET")
	api.HandleFunc("/failover/events", s.handleFailoverEvents).Methods("GET")
	api.HandleFunc("/failover/trigger/{nodeId}", s.handleFailoverTrigger).Methods("POST")

	api.HandleFunc("/cost/current", s.handleCostCurrent).Methods("GET")
	api.HandleFunc("/cost/predict/scaleup", s.handleCostPredictScaleUp).Methods("GET")
	api.HandleFunc("/cost/predict/scaledown", s.handleCostPredictScaleDown).Methods("GET")
	api.HandleFunc("/cost/predict/rebalance", s.handleCostPredictRebalance).Methods("GET")
	api.HandleFunc("/cost/predict/replica", s.handleCostPredictAddReplica).Methods("GET")

	api.HandleFunc("/simulate/scaleup", s.handleSimulateScaleUp).Methods("POST")
	api.HandleFunc("/simulate/scaledown", s.handleSimulateScaleDown).Methods("POST")
	api.HandleFunc("/simulate/rebalance", s.handleSimulateRebalance).Methods("POST")
	api.HandleFunc("/simulate/failover/{nodeId}", s.handleSimulateFailover).Methods("POST")
	api.HandleFunc("/simulate/results", s.handleSimulateResults).Methods("GET")

	s.router.PathPrefix("/").Handler(http.FileServer(http.Dir("./web/dist")))
}

func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func (s *Server) Start() error {
	srv := &http.Server{
		Addr:         s.addr,
		Handler:      s.router,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}
	return srv.ListenAndServe()
}

func respondJSON(w http.ResponseWriter, statusCode int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(data)
}

func respondError(w http.ResponseWriter, statusCode int, msg string) {
	respondJSON(w, statusCode, map[string]string{"error": msg})
}

func (s *Server) handleClusterInfo(w http.ResponseWriter, r *http.Request) {
	info, err := s.clusterMgr.GetClusterInfo(r.Context())
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	respondJSON(w, http.StatusOK, info)
}

func (s *Server) handleClusterNodes(w http.ResponseWriter, r *http.Request) {
	nodes, err := s.clusterMgr.GetNodes(r.Context())
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	respondJSON(w, http.StatusOK, nodes)
}

func (s *Server) handleClusterStats(w http.ResponseWriter, r *http.Request) {
	stats, err := s.clusterMgr.GetClusterStats(r.Context())
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	respondJSON(w, http.StatusOK, stats)
}

func (s *Server) handleSlotDistribution(w http.ResponseWriter, r *http.Request) {
	dist, err := s.clusterMgr.GetSlotDistribution(r.Context())
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	respondJSON(w, http.StatusOK, dist)
}

func (s *Server) handleMonitorCurrent(w http.ResponseWriter, r *http.Request) {
	metrics := s.monitor.GetLatest()
	if metrics == nil {
		respondError(w, http.StatusNotFound, "no metrics available yet")
		return
	}
	respondJSON(w, http.StatusOK, metrics)
}

func (s *Server) handleMonitorHistory(w http.ResponseWriter, r *http.Request) {
	history := s.monitor.GetHistory()
	respondJSON(w, http.StatusOK, history)
}

func (s *Server) handleMonitorRange(w http.ResponseWriter, r *http.Request) {
	fromStr := r.URL.Query().Get("from")
	toStr := r.URL.Query().Get("to")

	from, err1 := strconv.ParseInt(fromStr, 10, 64)
	to, err2 := strconv.ParseInt(toStr, 10, 64)
	if err1 != nil || err2 != nil {
		respondError(w, http.StatusBadRequest, "invalid from/to parameters")
		return
	}

	history := s.monitor.GetTimeRange(from, to)
	respondJSON(w, http.StatusOK, history)
}

func (s *Server) handleScalerEvents(w http.ResponseWriter, r *http.Request) {
	events := s.scaler.GetEvents()
	respondJSON(w, http.StatusOK, events)
}

func (s *Server) handleScalerAddNode(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Addr string `json:"addr"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	err := s.scaler.AddNewNode(r.Context(), req.Addr)
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}

	respondJSON(w, http.StatusOK, map[string]string{"status": "node added and rebalanced"})
}

func (s *Server) handleScalerRemoveNode(w http.ResponseWriter, r *http.Request) {
	var req struct {
		NodeID string `json:"node_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	err := s.scaler.RemoveNodeByID(r.Context(), req.NodeID)
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}

	respondJSON(w, http.StatusOK, map[string]string{"status": "node removed"})
}

func (s *Server) handleMigrationPlan(w http.ResponseWriter, r *http.Request) {
	plan, err := s.migrator.RebalancePlan(r.Context())
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	respondJSON(w, http.StatusOK, plan)
}

func (s *Server) handleMigrationExecute(w http.ResponseWriter, r *http.Request) {
	plan, err := s.migrator.RebalancePlan(r.Context())
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}

	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Hour)
		defer cancel()

		execErr := s.migrator.ExecutePlan(ctx, plan)

		if execErr == nil && s.backupMgr != nil {
			log.Printf("[API] Rebalance completed, triggering post-migration backup (explicit API layer)...")
			_, backupErr := s.backupMgr.CreateBackup(context.Background())
			if backupErr != nil {
				log.Printf("[API] Post-rebalance backup failed: %v", backupErr)
			} else {
				log.Printf("[API] Post-rebalance backup completed")
			}
		}
	}()

	respondJSON(w, http.StatusOK, map[string]string{"status": "rebalance started", "note": "backup will trigger automatically on completion"})
}

func (s *Server) handleMigrationEvacuate(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	nodeID := vars["nodeId"]

	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Hour)
		defer cancel()

		execErr := s.migrator.EvacuateNode(ctx, nodeID)

		if execErr == nil && s.backupMgr != nil {
			log.Printf("[API] Evacuation completed, triggering post-migration backup...")
			_, backupErr := s.backupMgr.CreateBackup(context.Background())
			if backupErr != nil {
				log.Printf("[API] Post-evacuation backup failed: %v", backupErr)
			} else {
				log.Printf("[API] Post-evacuation backup completed")
			}
		}
	}()

	respondJSON(w, http.StatusOK, map[string]string{"status": "evacuation started", "note": "backup will trigger automatically on completion"})
}

func (s *Server) handleMigrationMigrate(w http.ResponseWriter, r *http.Request) {
	var req struct {
		FromNodeID string   `json:"from_node_id"`
		ToNodeID   string   `json:"to_node_id"`
		Slots      []uint16 `json:"slots"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Hour)
		defer cancel()

		execErr := s.migrator.MigrateSlots(ctx, req.FromNodeID, req.ToNodeID, req.Slots)

		if execErr == nil && s.backupMgr != nil {
			log.Printf("[API] Slot migration completed, triggering post-migration backup...")
			_, backupErr := s.backupMgr.CreateBackup(context.Background())
			if backupErr != nil {
				log.Printf("[API] Post-migration backup failed: %v", backupErr)
			} else {
				log.Printf("[API] Post-migration backup completed")
			}
		}
	}()

	respondJSON(w, http.StatusOK, map[string]string{"status": "migration started", "note": "backup will trigger automatically on completion"})
}

func (s *Server) handleMigrationTasks(w http.ResponseWriter, r *http.Request) {
	tasks := s.migrator.GetActiveTasks()
	respondJSON(w, http.StatusOK, tasks)
}

func (s *Server) handleMigrationCancel(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	taskID := vars["taskId"]

	s.migrator.CancelMigration(taskID)
	respondJSON(w, http.StatusOK, map[string]string{"status": "cancellation requested"})
}

func (s *Server) handleBackupList(w http.ResponseWriter, r *http.Request) {
	records := s.backupMgr.GetRecords()
	respondJSON(w, http.StatusOK, records)
}

func (s *Server) handleBackupCreate(w http.ResponseWriter, r *http.Request) {
	record, err := s.backupMgr.CreateBackup(r.Context())
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	respondJSON(w, http.StatusOK, record)
}

func (s *Server) handleFailoverHealth(w http.ResponseWriter, r *http.Request) {
	health := s.failoverMgr.GetAllHealth()
	respondJSON(w, http.StatusOK, health)
}

func (s *Server) handleFailoverEvents(w http.ResponseWriter, r *http.Request) {
	events := s.failoverMgr.GetEvents()
	respondJSON(w, http.StatusOK, events)
}

func (s *Server) handleFailoverTrigger(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	nodeID := vars["nodeId"]

	event, err := s.failoverMgr.TriggerManualFailover(r.Context(), nodeID)
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	respondJSON(w, http.StatusOK, event)
}

func (s *Server) handleCostCurrent(w http.ResponseWriter, r *http.Request) {
	summary, err := s.costMgr.GetCurrentCost(r.Context())
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	respondJSON(w, http.StatusOK, summary)
}

func (s *Server) handleCostPredictScaleUp(w http.ResponseWriter, r *http.Request) {
	nodesStr := r.URL.Query().Get("nodes")
	nodes, err := strconv.Atoi(nodesStr)
	if err != nil {
		nodes = 1
	}

	pred, err := s.costMgr.PredictScaleUp(r.Context(), nodes)
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	respondJSON(w, http.StatusOK, pred)
}

func (s *Server) handleCostPredictScaleDown(w http.ResponseWriter, r *http.Request) {
	nodesStr := r.URL.Query().Get("nodes")
	nodes, err := strconv.Atoi(nodesStr)
	if err != nil {
		nodes = 1
	}

	pred, err := s.costMgr.PredictScaleDown(r.Context(), nodes)
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	respondJSON(w, http.StatusOK, pred)
}

func (s *Server) handleCostPredictRebalance(w http.ResponseWriter, r *http.Request) {
	pred, err := s.costMgr.PredictRebalance(r.Context())
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	respondJSON(w, http.StatusOK, pred)
}

func (s *Server) handleCostPredictAddReplica(w http.ResponseWriter, r *http.Request) {
	nodesStr := r.URL.Query().Get("nodes")
	nodes, err := strconv.Atoi(nodesStr)
	if err != nil {
		nodes = 1
	}

	pred, err := s.costMgr.PredictAddReplica(r.Context(), nodes)
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	respondJSON(w, http.StatusOK, pred)
}

func (s *Server) handleSimulateScaleUp(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Nodes int `json:"nodes"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		req.Nodes = 1
	}

	result, err := s.simulationMgr.SimulateScaleUp(r.Context(), req.Nodes)
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	respondJSON(w, http.StatusOK, result)
}

func (s *Server) handleSimulateScaleDown(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Nodes int `json:"nodes"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		req.Nodes = 1
	}

	result, err := s.simulationMgr.SimulateScaleDown(r.Context(), req.Nodes)
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	respondJSON(w, http.StatusOK, result)
}

func (s *Server) handleSimulateRebalance(w http.ResponseWriter, r *http.Request) {
	result, err := s.simulationMgr.SimulateRebalance(r.Context())
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	respondJSON(w, http.StatusOK, result)
}

func (s *Server) handleSimulateFailover(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	nodeID := vars["nodeId"]

	result, err := s.simulationMgr.SimulateFailover(r.Context(), nodeID)
	if err != nil {
		respondError(w, http.StatusInternalServerError, err.Error())
		return
	}
	respondJSON(w, http.StatusOK, result)
}

func (s *Server) handleSimulateResults(w http.ResponseWriter, r *http.Request) {
	results := s.simulationMgr.GetResults()
	respondJSON(w, http.StatusOK, results)
}
