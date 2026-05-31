package api

import (
	"context"
	"encoding/json"
	"net/http"
	"strconv"
	"time"

	"github.com/gorilla/mux"
	"github.com/k8s-autoscaler/pkg/benefit"
	"github.com/k8s-autoscaler/pkg/controller"
	"github.com/k8s-autoscaler/pkg/linkage"
)

type APIResponse struct {
	Success bool        `json:"success"`
	Data    interface{} `json:"data,omitempty"`
	Error   string      `json:"error,omitempty"`
}

type Server struct {
	controller *controller.Controller
	router     *mux.Router
	port       int
	httpServer *http.Server
}

type ScaleRequest struct {
	Replicas int32 `json:"replicas"`
}

func NewServer(ctrl *controller.Controller, port int) *Server {
	s := &Server{
		controller: ctrl,
		router:     mux.NewRouter(),
		port:       port,
	}
	s.SetupRoutes()
	return s
}

func (s *Server) SetupRoutes() {
	s.router.HandleFunc("/api/v1/namespaces/{namespace}/deployments/{deployment}/metrics", s.getMetrics).Methods("GET")
	s.router.HandleFunc("/api/v1/namespaces/{namespace}/deployments/{deployment}/recommendation", s.getRecommendation).Methods("GET")
	s.router.HandleFunc("/api/v1/namespaces/{namespace}/deployments/{deployment}/prediction", s.getPrediction).Methods("GET")
	s.router.HandleFunc("/api/v1/namespaces/{namespace}/deployments/{deployment}/cost", s.getCost).Methods("GET")
	s.router.HandleFunc("/api/v1/namespaces/{namespace}/deployments/{deployment}/autotune", s.getAutotune).Methods("GET")
	s.router.HandleFunc("/api/v1/namespaces/{namespace}/deployments/{deployment}/scale", s.scaleDeployment).Methods("POST")
	s.router.HandleFunc("/api/v1/namespaces/{namespace}/deployments/{deployment}/watch", s.addWatch).Methods("POST")
	s.router.HandleFunc("/api/v1/namespaces/{namespace}/deployments/{deployment}/watch", s.removeWatch).Methods("DELETE")
	s.router.HandleFunc("/api/v1/dashboard", s.getDashboard).Methods("GET")
	s.router.HandleFunc("/api/v1/tuning", s.getTuning).Methods("GET")
	s.router.HandleFunc("/api/v1/tuning/history", s.getTuningHistory).Methods("GET")
	s.router.HandleFunc("/api/v1/linkages", s.getLinkages).Methods("GET")
	s.router.HandleFunc("/api/v1/linkages", s.addLinkage).Methods("POST")
	s.router.HandleFunc("/api/v1/linkages/pending", s.getPendingLinkages).Methods("GET")
	s.router.HandleFunc("/api/v1/cost-benefit/history", s.getCostBenefitHistory).Methods("GET")
	s.router.HandleFunc("/api/v1/health", s.healthCheck).Methods("GET")
	s.router.Use(s.corsMiddleware)
}

func (s *Server) Start() error {
	s.httpServer = &http.Server{
		Addr:    ":" + strconv.Itoa(s.port),
		Handler: s.router,
	}
	return s.httpServer.ListenAndServe()
}

func (s *Server) Stop() {
	if s.httpServer != nil {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		s.httpServer.Shutdown(ctx)
	}
}

func (s *Server) corsMiddleware(next http.Handler) http.Handler {
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

func (s *Server) writeJSON(w http.ResponseWriter, statusCode int, data APIResponse) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(data)
}

func (s *Server) getMetrics(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	namespace := vars["namespace"]
	deployment := vars["deployment"]

	result, err := s.controller.GetMetrics(namespace, deployment)
	if err != nil {
		s.writeJSON(w, http.StatusInternalServerError, APIResponse{Success: false, Error: err.Error()})
		return
	}
	s.writeJSON(w, http.StatusOK, APIResponse{Success: true, Data: result})
}

func (s *Server) getRecommendation(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	namespace := vars["namespace"]
	deployment := vars["deployment"]

	result, err := s.controller.GetRecommendation(namespace, deployment)
	if err != nil {
		s.writeJSON(w, http.StatusInternalServerError, APIResponse{Success: false, Error: err.Error()})
		return
	}
	s.writeJSON(w, http.StatusOK, APIResponse{Success: true, Data: result})
}

func (s *Server) getPrediction(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	namespace := vars["namespace"]
	deployment := vars["deployment"]

	result, err := s.controller.GetPrediction(namespace, deployment)
	if err != nil {
		s.writeJSON(w, http.StatusInternalServerError, APIResponse{Success: false, Error: err.Error()})
		return
	}
	s.writeJSON(w, http.StatusOK, APIResponse{Success: true, Data: result})
}

func (s *Server) getCost(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	namespace := vars["namespace"]
	deployment := vars["deployment"]

	result, err := s.controller.GetCost(namespace, deployment)
	if err != nil {
		s.writeJSON(w, http.StatusInternalServerError, APIResponse{Success: false, Error: err.Error()})
		return
	}
	s.writeJSON(w, http.StatusOK, APIResponse{Success: true, Data: result})
}

func (s *Server) getAutotune(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	namespace := vars["namespace"]
	deployment := vars["deployment"]

	result, err := s.controller.GetAutotune(namespace, deployment)
	if err != nil {
		s.writeJSON(w, http.StatusInternalServerError, APIResponse{Success: false, Error: err.Error()})
		return
	}
	s.writeJSON(w, http.StatusOK, APIResponse{Success: true, Data: result})
}

func (s *Server) scaleDeployment(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	namespace := vars["namespace"]
	deployment := vars["deployment"]

	var req ScaleRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		s.writeJSON(w, http.StatusBadRequest, APIResponse{Success: false, Error: "invalid request body"})
		return
	}

	err := s.controller.Scale(namespace, deployment, req.Replicas)
	if err != nil {
		s.writeJSON(w, http.StatusInternalServerError, APIResponse{Success: false, Error: err.Error()})
		return
	}
	s.writeJSON(w, http.StatusOK, APIResponse{Success: true, Data: map[string]string{"message": "scaling applied"}})
}

func (s *Server) addWatch(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	namespace := vars["namespace"]
	deployment := vars["deployment"]

	err := s.controller.AddWatch(namespace, deployment)
	if err != nil {
		s.writeJSON(w, http.StatusInternalServerError, APIResponse{Success: false, Error: err.Error()})
		return
	}
	s.writeJSON(w, http.StatusOK, APIResponse{Success: true, Data: map[string]string{"message": "deployment added to watch list"}})
}

func (s *Server) removeWatch(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	namespace := vars["namespace"]
	deployment := vars["deployment"]

	err := s.controller.RemoveWatch(namespace, deployment)
	if err != nil {
		s.writeJSON(w, http.StatusInternalServerError, APIResponse{Success: false, Error: err.Error()})
		return
	}
	s.writeJSON(w, http.StatusOK, APIResponse{Success: true, Data: map[string]string{"message": "deployment removed from watch list"}})
}

func (s *Server) getDashboard(w http.ResponseWriter, r *http.Request) {
	result, err := s.controller.GetDashboard()
	if err != nil {
		s.writeJSON(w, http.StatusInternalServerError, APIResponse{Success: false, Error: err.Error()})
		return
	}
	s.writeJSON(w, http.StatusOK, APIResponse{Success: true, Data: result})
}

func (s *Server) getTuning(w http.ResponseWriter, r *http.Request) {
	result, err := s.controller.GetTuningResult()
	if err != nil {
		s.writeJSON(w, http.StatusInternalServerError, APIResponse{Success: false, Error: err.Error()})
		return
	}
	s.writeJSON(w, http.StatusOK, APIResponse{Success: true, Data: result})
}

func (s *Server) getTuningHistory(w http.ResponseWriter, r *http.Request) {
	result, err := s.controller.GetTuningHistory()
	if err != nil {
		s.writeJSON(w, http.StatusInternalServerError, APIResponse{Success: false, Error: err.Error()})
		return
	}
	s.writeJSON(w, http.StatusOK, APIResponse{Success: true, Data: result})
}

func (s *Server) getLinkages(w http.ResponseWriter, r *http.Request) {
	result, err := s.controller.GetLinkages()
	if err != nil {
		s.writeJSON(w, http.StatusInternalServerError, APIResponse{Success: false, Error: err.Error()})
		return
	}
	s.writeJSON(w, http.StatusOK, APIResponse{Success: true, Data: result})
}

func (s *Server) addLinkage(w http.ResponseWriter, r *http.Request) {
	var dep linkage.ServiceDependency
	if err := json.NewDecoder(r.Body).Decode(&dep); err != nil {
		s.writeJSON(w, http.StatusBadRequest, APIResponse{Success: false, Error: "invalid request body"})
		return
	}

	err := s.controller.AddLinkage(dep)
	if err != nil {
		s.writeJSON(w, http.StatusInternalServerError, APIResponse{Success: false, Error: err.Error()})
		return
	}
	s.writeJSON(w, http.StatusOK, APIResponse{Success: true, Data: map[string]string{"message": "linkage added"}})
}

func (s *Server) getPendingLinkages(w http.ResponseWriter, r *http.Request) {
	result, err := s.controller.GetPendingLinkages()
	if err != nil {
		s.writeJSON(w, http.StatusInternalServerError, APIResponse{Success: false, Error: err.Error()})
		return
	}
	s.writeJSON(w, http.StatusOK, APIResponse{Success: true, Data: result})
}

func (s *Server) getCostBenefitHistory(w http.ResponseWriter, r *http.Request) {
	result, err := s.controller.GetCostBenefitHistory()
	if err != nil {
		s.writeJSON(w, http.StatusInternalServerError, APIResponse{Success: false, Error: err.Error()})
		return
	}
	s.writeJSON(w, http.StatusOK, APIResponse{Success: true, Data: result})
}

func (s *Server) healthCheck(w http.ResponseWriter, r *http.Request) {
	s.writeJSON(w, http.StatusOK, APIResponse{Success: true, Data: map[string]string{"status": "healthy"}})
}
