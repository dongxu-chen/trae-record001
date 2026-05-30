package container

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	dockertypes "github.com/docker/docker/api/types"
	"github.com/docker/docker/client"
	"github.com/sirupsen/logrus"

	apptypes "github.com/security/container-escape-detector/pkg/types"
)

type Config struct {
	RefreshInterval int
	DockerSocket    string
	UseProcFS       bool
	UseDockerAPI    bool
}

type Manager struct {
	containers      map[string]*apptypes.ContainerInfo
	pidToContainer  map[uint32]string
	pidnsToContainer map[uint64]string
	mntnsToContainer map[uint64]string
	mu              sync.RWMutex
	dockerClient    *client.Client
	logger          *logrus.Logger
	refreshInterval time.Duration
	config          *Config
	ctx             context.Context
	cancel          context.CancelFunc
	wg              sync.WaitGroup
}

func NewManager(logger *logrus.Logger, config *Config) *Manager {
	if config == nil {
		config = &Config{
			RefreshInterval: 30,
			DockerSocket:    "/var/run/docker.sock",
			UseProcFS:       true,
			UseDockerAPI:    true,
		}
	}

	ctx, cancel := context.WithCancel(context.Background())

	var cli *client.Client
	if config.UseDockerAPI {
		var err error
		cli, err = client.NewClientWithOpts(client.FromEnv, client.WithAPIVersionNegotiation())
		if err != nil {
			logger.Warnf("Failed to create Docker client: %v, will use /proc fallback", err)
		}
	}

	refreshInterval := time.Duration(config.RefreshInterval) * time.Second
	if refreshInterval < 5*time.Second {
		refreshInterval = 30 * time.Second
	}

	return &Manager{
		containers:       make(map[string]*apptypes.ContainerInfo),
		pidToContainer:   make(map[uint32]string),
		pidnsToContainer: make(map[uint64]string),
		mntnsToContainer: make(map[uint64]string),
		dockerClient:     cli,
		logger:           logger,
		refreshInterval:  refreshInterval,
		config:           config,
		ctx:              ctx,
		cancel:           cancel,
	}
}

func (m *Manager) Init() error {
	if err := m.refreshContainers(); err != nil {
		m.logger.Errorf("Initial container refresh failed: %v", err)
	}

	m.wg.Add(1)
	go m.refreshLoop()

	m.logger.Info("Container manager initialized")
	return nil
}

func (m *Manager) Start() error {
	return m.Init()
}

func (m *Manager) refreshLoop() {
	defer m.wg.Done()

	ticker := time.NewTicker(m.refreshInterval)
	defer ticker.Stop()

	for {
		select {
		case <-m.ctx.Done():
			return
		case <-ticker.C:
			if err := m.refreshContainers(); err != nil {
				m.logger.Errorf("Container refresh failed: %v", err)
			}
		}
	}
}

func (m *Manager) refreshContainers() error {
	if m.dockerClient != nil {
		if err := m.refreshFromDocker(); err == nil {
			return nil
		}
	}

	return m.refreshFromProc()
}

func (m *Manager) refreshFromDocker() error {
	containers, err := m.dockerClient.ContainerList(m.ctx, dockertypes.ContainerListOptions{All: false})
	if err != nil {
		return fmt.Errorf("failed to list containers: %w", err)
	}

	newContainers := make(map[string]*apptypes.ContainerInfo)
	newPIDMap := make(map[uint32]string)
	newPIDNSMap := make(map[uint64]string)
	newMNTNSMap := make(map[uint64]string)

	for _, c := range containers {
		info, err := m.getContainerInfo(c.ID)
		if err != nil {
			m.logger.Warnf("Failed to get info for container %s: %v", c.ID[:12], err)
			continue
		}

		newContainers[info.ID] = info
		newPIDMap[uint32(info.PID)] = info.ID

		if info.PIDNS != 0 {
			newPIDNSMap[info.PIDNS] = info.ID
		}
		if info.MNTNS != 0 {
			newMNTNSMap[info.MNTNS] = info.ID
		}

		childPIDs, err := m.getChildPIDs(info.PID)
		if err == nil {
			for _, pid := range childPIDs {
				newPIDMap[uint32(pid)] = info.ID

				pidns, err := getPIDNS(pid)
				if err == nil {
					newPIDNSMap[pidns] = info.ID
				}
				mntns, err := getMNTNS(pid)
				if err == nil {
					newMNTNSMap[mntns] = info.ID
				}
			}
		}
	}

	m.mu.Lock()
	m.containers = newContainers
	m.pidToContainer = newPIDMap
	m.pidnsToContainer = newPIDNSMap
	m.mntnsToContainer = newMNTNSMap
	m.mu.Unlock()

	m.logger.Debugf("Refreshed %d containers from Docker", len(newContainers))
	return nil
}

func (m *Manager) getContainerInfo(containerID string) (*apptypes.ContainerInfo, error) {
	jsonInfo, err := m.dockerClient.ContainerInspect(m.ctx, containerID)
	if err != nil {
		return nil, fmt.Errorf("failed to inspect container: %w", err)
	}

	info := &apptypes.ContainerInfo{
		ID:         jsonInfo.ID,
		Name:       strings.TrimPrefix(jsonInfo.Name, "/"),
		Image:      jsonInfo.Config.Image,
		PID:        jsonInfo.State.Pid,
		Privileged: jsonInfo.HostConfig.Privileged,
		CreatedAt:  jsonInfo.Created,
		Labels:     jsonInfo.Config.Labels,
	}

	if jsonInfo.NetworkSettings != nil && len(jsonInfo.NetworkSettings.IPAddress) > 0 {
		info.IPAddress = jsonInfo.NetworkSettings.IPAddress
	} else if jsonInfo.NetworkSettings != nil {
		for _, net := range jsonInfo.NetworkSettings.Networks {
			if net.IPAddress != "" {
				info.IPAddress = net.IPAddress
				break
			}
		}
	}

	if jsonInfo.HostConfig != nil {
		for _, cap := range jsonInfo.HostConfig.CapAdd {
			info.Capabilities = append(info.Capabilities, strings.ToUpper(cap))
		}
	}

	for _, m := range jsonInfo.Mounts {
		mp := apptypes.MountPoint{
			Source:      m.Source,
			Destination: m.Destination,
			Mode:        m.Mode,
			RW:          m.RW,
			IsSensitive: isSensitivePath(m.Source),
		}
		info.Mounts = append(info.Mounts, mp)
	}

	if info.PID > 0 {
		info.PIDNS, _ = getPIDNS(info.PID)
		info.MNTNS, _ = getMNTNS(info.PID)
		info.NETNS, _ = getNETNS(info.PID)
		info.UserNS, _ = getUSERNS(info.PID)
	}

	return info, nil
}

func (m *Manager) refreshFromProc() error {
	newContainers := make(map[string]*apptypes.ContainerInfo)
	newPIDMap := make(map[uint32]string)
	newPIDNSMap := make(map[uint64]string)
	newMNTNSMap := make(map[uint64]string)

	entries, err := os.ReadDir("/proc")
	if err != nil {
		return fmt.Errorf("failed to read /proc: %w", err)
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}

		pid, err := strconv.Atoi(entry.Name())
		if err != nil {
			continue
		}

		cgroupPath := filepath.Join("/proc", entry.Name(), "cgroup")
		cgroupData, err := os.ReadFile(cgroupPath)
		if err != nil {
			continue
		}

		containerID := extractContainerID(string(cgroupData))
		if containerID == "" {
			continue
		}

		pidns, _ := getPIDNS(pid)
		mntns, _ := getMNTNS(pid)

		if _, exists := newContainers[containerID]; !exists {
			info := &apptypes.ContainerInfo{
				ID:        containerID,
				Name:      fmt.Sprintf("container_%s", containerID[:12]),
				PID:       pid,
				PIDNS:     pidns,
				MNTNS:     mntns,
				CreatedAt: time.Now(),
			}

			info.Privileged = isPrivilegedContainer(pid)
			info.Capabilities = getProcessCapabilities(pid)

			newContainers[containerID] = info
			newPIDNSMap[pidns] = containerID
			newMNTNSMap[mntns] = containerID
		}

		newPIDMap[uint32(pid)] = containerID
	}

	m.mu.Lock()
	m.containers = newContainers
	m.pidToContainer = newPIDMap
	m.pidnsToContainer = newPIDNSMap
	m.mntnsToContainer = newMNTNSMap
	m.mu.Unlock()

	m.logger.Debugf("Refreshed %d containers from /proc", len(newContainers))
	return nil
}

func (m *Manager) getChildPIDs(ppid int) ([]int, error) {
	var children []int

	entries, err := os.ReadDir("/proc")
	if err != nil {
		return nil, err
	}

	for _, entry := range entries {
		pid, err := strconv.Atoi(entry.Name())
		if err != nil {
			continue
		}

		statusPath := filepath.Join("/proc", entry.Name(), "status")
		statusData, err := os.ReadFile(statusPath)
		if err != nil {
			continue
		}

		for _, line := range strings.Split(string(statusData), "\n") {
			if strings.HasPrefix(line, "PPid:") {
				parts := strings.Fields(line)
				if len(parts) >= 2 {
					parentPID, _ := strconv.Atoi(parts[1])
					if parentPID == ppid {
						children = append(children, pid)
					}
				}
				break
			}
		}
	}

	return children, nil
}

func (m *Manager) GetContainerByPID(pid uint32) (*apptypes.ContainerInfo, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	containerID, ok := m.pidToContainer[pid]
	if !ok {
		return nil, false
	}

	container, exists := m.containers[containerID]
	return container, exists
}

func (m *Manager) GetContainerByPIDNS(pidns uint64) (*apptypes.ContainerInfo, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	containerID, ok := m.pidnsToContainer[pidns]
	if !ok {
		return nil, false
	}

	container, exists := m.containers[containerID]
	return container, exists
}

func (m *Manager) GetContainerByMNTNS(mntns uint64) (*apptypes.ContainerInfo, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	containerID, ok := m.mntnsToContainer[mntns]
	if !ok {
		return nil, false
	}

	container, exists := m.containers[containerID]
	return container, exists
}

func (m *Manager) GetContainer(id string) (*apptypes.ContainerInfo, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	container, exists := m.containers[id]
	return container, exists
}

func (m *Manager) GetAllContainers() []*apptypes.ContainerInfo {
	m.mu.RLock()
	defer m.mu.RUnlock()

	containers := make([]*apptypes.ContainerInfo, 0, len(m.containers))
	for _, c := range m.containers {
		containers = append(containers, c)
	}
	return containers
}

func (m *Manager) AssociateProcess(pid uint32, pidns uint64, mntns uint64) *apptypes.ContainerInfo {
	if container, ok := m.GetContainerByPID(pid); ok {
		return container
	}

	if pidns != 0 {
		if container, ok := m.GetContainerByPIDNS(pidns); ok {
			return container
		}
	}

	if mntns != 0 {
		if container, ok := m.GetContainerByMNTNS(mntns); ok {
			return container
		}
	}

	return nil
}

func (m *Manager) GetProcessInfo(pid int) (*apptypes.ProcessInfo, error) {
	info := &apptypes.ProcessInfo{
		PID: pid,
	}

	statusPath := filepath.Join("/proc", strconv.Itoa(pid), "status")
	statusData, err := os.ReadFile(statusPath)
	if err != nil {
		return nil, err
	}

	for _, line := range strings.Split(string(statusData), "\n") {
		parts := strings.Fields(line)
		if len(parts) < 2 {
			continue
		}

		switch parts[0] {
		case "Name:":
			info.Comm = parts[1]
		case "PPid:":
			info.PPID, _ = strconv.Atoi(parts[1])
		case "Uid:":
			if len(parts) >= 2 {
				uid, _ := strconv.ParseUint(parts[1], 10, 32)
				info.UID = uint32(uid)
			}
		case "Gid:":
			if len(parts) >= 2 {
				gid, _ := strconv.ParseUint(parts[1], 10, 32)
				info.GID = uint32(gid)
			}
		}
	}

	exePath := filepath.Join("/proc", strconv.Itoa(pid), "exe")
	if exe, err := os.Readlink(exePath); err == nil {
		info.Exe = exe
	}

	cmdlinePath := filepath.Join("/proc", strconv.Itoa(pid), "cmdline")
	if cmdlineData, err := os.ReadFile(cmdlinePath); err == nil {
		info.CmdLine = strings.Split(string(cmdlineData), "\x00")
	}

	info.CapEffective, info.CapPermitted = getProcessCapBits(pid)

	if container, ok := m.GetContainerByPID(uint32(pid)); ok {
		info.ContainerID = container.ID
	}

	return info, nil
}

func (m *Manager) Close() {
	m.cancel()
	m.wg.Wait()

	if m.dockerClient != nil {
		m.dockerClient.Close()
	}

	m.logger.Info("Container manager closed")
}

func extractContainerID(cgroupData string) string {
	for _, line := range strings.Split(cgroupData, "\n") {
		if strings.Contains(line, "docker") || strings.Contains(line, "kubepods") {
			fields := strings.Split(line, "/")
			for i := len(fields) - 1; i >= 0; i-- {
				field := fields[i]
				if len(field) == 64 || strings.HasPrefix(field, "docker-") {
					if strings.HasPrefix(field, "docker-") {
						field = strings.TrimPrefix(field, "docker-")
						field = strings.TrimSuffix(field, ".scope")
					}
					if len(field) >= 12 {
						return field
					}
				}
			}
		}
	}
	return ""
}

func isSensitivePath(path string) bool {
	for _, sp := range apptypes.SensitivePaths {
		if strings.HasPrefix(path, sp) {
			return true
		}
	}
	return false
}

func getNS(pid int, nsType string) (uint64, error) {
	nsPath := filepath.Join("/proc", strconv.Itoa(pid), "ns", nsType)
	link, err := os.Readlink(nsPath)
	if err != nil {
		return 0, err
	}

	parts := strings.Split(link, "[")
	if len(parts) != 2 {
		return 0, fmt.Errorf("invalid ns link format: %s", link)
	}

	nsStr := strings.TrimSuffix(parts[1], "]")
	return strconv.ParseUint(nsStr, 10, 64)
}

func getPIDNS(pid int) (uint64, error)  { return getNS(pid, "pid") }
func getMNTNS(pid int) (uint64, error)  { return getNS(pid, "mnt") }
func getNETNS(pid int) (uint64, error)  { return getNS(pid, "net") }
func getUSERNS(pid int) (uint64, error) { return getNS(pid, "user") }

func isPrivilegedContainer(pid int) bool {
	capEff, capPerm := getProcessCapBits(pid)
	allCaps := uint64(0x3FFFFFFFFF)
	return capEff == allCaps || capPerm == allCaps
}

func getProcessCapabilities(pid int) []string {
	capEff, _ := getProcessCapBits(pid)
	var caps []string

	for i := uint32(0); i < 64; i++ {
		if capEff&(1<<i) != 0 {
			if name, ok := apptypes.CapabilityNames[i]; ok {
				caps = append(caps, name)
			}
		}
	}

	return caps
}

func getProcessCapBits(pid int) (uint64, uint64) {
	statusPath := filepath.Join("/proc", strconv.Itoa(pid), "status")
	statusData, err := os.ReadFile(statusPath)
	if err != nil {
		return 0, 0
	}

	var capEff, capPerm uint64

	for _, line := range strings.Split(string(statusData), "\n") {
		parts := strings.Fields(line)
		if len(parts) < 2 {
			continue
		}

		switch parts[0] {
		case "CapEff:":
			capEff, _ = strconv.ParseUint(parts[1], 16, 64)
		case "CapPrm:":
			capPerm, _ = strconv.ParseUint(parts[1], 16, 64)
		}
	}

	return capEff, capPerm
}
