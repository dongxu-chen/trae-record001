package discovery

import (
	"context"
	"encoding/json"
	"fmt"
	"path"
	"scheduler/internal/models"
	"time"

	"go.etcd.io/etcd/api/v3/mvccpb"
	clientv3 "go.etcd.io/etcd/client/v3"
)

type EtcdClient struct {
	client     *clientv3.Client
	rootPrefix string
	leaseTTL   int64
	leaseID    clientv3.LeaseID
}

func NewEtcdClient(endpoints []string, dialTimeout int, rootPrefix string, leaseTTL int64) (*EtcdClient, error) {
	client, err := clientv3.New(clientv3.Config{
		Endpoints:   endpoints,
		DialTimeout: time.Duration(dialTimeout) * time.Millisecond,
	})
	if err != nil {
		return nil, err
	}

	return &EtcdClient{
		client:     client,
		rootPrefix: rootPrefix,
		leaseTTL:   leaseTTL,
	}, nil
}

func (e *EtcdClient) Close() error {
	return e.client.Close()
}

func (e *EtcdClient) getKey(keys ...string) string {
	return path.Join(e.rootPrefix, path.Join(keys...))
}

func (e *EtcdClient) RegisterNode(ctx context.Context, node *models.Node) error {
	lease, err := e.client.Grant(ctx, e.leaseTTL)
	if err != nil {
		return err
	}
	e.leaseID = lease.ID

	nodeData, err := json.Marshal(node)
	if err != nil {
		return err
	}

	key := e.getKey("nodes", node.ID)
	_, err = e.client.Put(ctx, key, string(nodeData), clientv3.WithLease(lease.ID))
	if err != nil {
		return err
	}

	keepAliveCh, err := e.client.KeepAlive(ctx, lease.ID)
	if err != nil {
		return err
	}

	go func() {
		for {
			select {
			case <-ctx.Done():
				return
			case resp, ok := <-keepAliveCh:
				if !ok {
					return
				}
				_ = resp
			}
		}
	}()

	return nil
}

func (e *EtcdClient) DeregisterNode(ctx context.Context, nodeID string) error {
	key := e.getKey("nodes", nodeID)
	_, err := e.client.Delete(ctx, key)
	if e.leaseID != 0 {
		_, _ = e.client.Revoke(ctx, e.leaseID)
	}
	return err
}

func (e *EtcdClient) GetAllNodes(ctx context.Context) ([]*models.Node, error) {
	key := e.getKey("nodes") + "/"
	resp, err := e.client.Get(ctx, key, clientv3.WithPrefix())
	if err != nil {
		return nil, err
	}

	var nodes []*models.Node
	for _, kv := range resp.Kvs {
		node := &models.Node{}
		if err := json.Unmarshal(kv.Value, node); err != nil {
			continue
		}
		nodes = append(nodes, node)
	}
	return nodes, nil
}

func (e *EtcdClient) WatchNodes(ctx context.Context, onChange func()) {
	key := e.getKey("nodes") + "/"
	watchCh := e.client.Watch(ctx, key, clientv3.WithPrefix())

	go func() {
		for {
			select {
			case <-ctx.Done():
				return
			case resp, ok := <-watchCh:
				if !ok {
					return
				}
				if resp.Err() != nil {
					continue
				}
				onChange()
			}
		}
	}()
}

type DistributedLock struct {
	client  *EtcdClient
	key     string
	leaseID clientv3.LeaseID
	ctx     context.Context
	cancel  context.CancelFunc
}

func (e *EtcdClient) NewLock(name string) *DistributedLock {
	return &DistributedLock{
		client: e,
		key:    e.getKey("locks", name),
	}
}

func (l *DistributedLock) Lock(ctx context.Context, ttl int64) error {
	lease, err := l.client.client.Grant(ctx, ttl)
	if err != nil {
		return err
	}

	txn := l.client.client.Txn(ctx)
	txn = txn.If(
		clientv3.Compare(clientv3.CreateRevision(l.key), "=", 0),
	).Then(
		clientv3.OpPut(l.key, "", clientv3.WithLease(lease.ID)),
	).Else(
		clientv3.OpGet(l.key),
	)

	resp, err := txn.Commit()
	if err != nil {
		return err
	}

	if !resp.Succeeded {
		return fmt.Errorf("lock is held by another process")
	}

	l.leaseID = lease.ID
	l.ctx, l.cancel = context.WithCancel(ctx)

	keepAliveCh, err := l.client.client.KeepAlive(l.ctx, lease.ID)
	if err != nil {
		l.Unlock(ctx)
		return err
	}

	go func() {
		for {
			select {
			case <-l.ctx.Done():
				return
			case _, ok := <-keepAliveCh:
				if !ok {
					return
				}
			}
		}
	}()

	return nil
}

func (l *DistributedLock) Unlock(ctx context.Context) error {
	if l.cancel != nil {
		l.cancel()
	}

	if l.leaseID != 0 {
		_, _ = l.client.client.Revoke(ctx, l.leaseID)
		l.leaseID = 0
	}

	_, err := l.client.client.Delete(ctx, l.key)
	return err
}

func (e *EtcdClient) TryLock(ctx context.Context, name string, ttl int64) (*DistributedLock, error) {
	lock := e.NewLock(name)
	if err := lock.Lock(ctx, ttl); err != nil {
		return nil, err
	}
	return lock, nil
}

func (e *EtcdClient) ElectLeader(ctx context.Context, nodeID string) (bool, error) {
	lock := e.NewLock("leader")
	err := lock.Lock(ctx, e.leaseTTL)
	if err != nil {
		return false, nil
	}
	return true, nil
}

type TaskAssignment struct {
	TaskID   string `json:"task_id"`
	NodeID   string `json:"node_id"`
	Priority int    `json:"priority"`
}

func (e *EtcdClient) AssignTask(ctx context.Context, taskID, nodeID string, priority int) error {
	assignment := &TaskAssignment{
		TaskID:   taskID,
		NodeID:   nodeID,
		Priority: priority,
	}
	data, err := json.Marshal(assignment)
	if err != nil {
		return err
	}

	key := e.getKey("assignments", taskID)
	_, err = e.client.Put(ctx, key, string(data))
	return err
}

func (e *EtcdClient) UnassignTask(ctx context.Context, taskID string) error {
	key := e.getKey("assignments", taskID)
	_, err := e.client.Delete(ctx, key)
	return err
}

func (e *EtcdClient) GetTaskAssignment(ctx context.Context, taskID string) (*TaskAssignment, error) {
	key := e.getKey("assignments", taskID)
	resp, err := e.client.Get(ctx, key)
	if err != nil {
		return nil, err
	}

	if len(resp.Kvs) == 0 {
		return nil, nil
	}

	assignment := &TaskAssignment{}
	if err := json.Unmarshal(resp.Kvs[0].Value, assignment); err != nil {
		return nil, err
	}
	return assignment, nil
}

func (e *EtcdClient) GetAllAssignments(ctx context.Context) (map[string]*TaskAssignment, error) {
	key := e.getKey("assignments") + "/"
	resp, err := e.client.Get(ctx, key, clientv3.WithPrefix())
	if err != nil {
		return nil, err
	}

	assignments := make(map[string]*TaskAssignment)
	for _, kv := range resp.Kvs {
		assignment := &TaskAssignment{}
		if err := json.Unmarshal(kv.Value, assignment); err != nil {
			continue
		}
		assignments[assignment.TaskID] = assignment
	}
	return assignments, nil
}

func (e *EtcdClient) WatchAssignments(ctx context.Context, onChange func(taskID string, eventType mvccpb.Event_EventType)) {
	key := e.getKey("assignments") + "/"
	watchCh := e.client.Watch(ctx, key, clientv3.WithPrefix())

	go func() {
		for {
			select {
			case <-ctx.Done():
				return
			case resp, ok := <-watchCh:
				if !ok {
					return
				}
				if resp.Err() != nil {
					continue
				}
				for _, event := range resp.Events {
					taskID := path.Base(string(event.Kv.Key))
					onChange(taskID, event.Type)
				}
			}
		}
	}()
}

func (e *EtcdClient) SetSchedulerStatus(ctx context.Context, nodeID string, status string) error {
	key := e.getKey("scheduler", nodeID, "status")
	_, err := e.client.Put(ctx, key, status)
	return err
}

func (e *EtcdClient) UpdateTaskCount(ctx context.Context, nodeID string, count int) error {
	key := e.getKey("scheduler", nodeID, "task_count")
	_, err := e.client.Put(ctx, key, fmt.Sprintf("%d", count))
	return err
}

func (e *EtcdClient) GetSchedulerStats(ctx context.Context) (map[string]int, error) {
	key := e.getKey("scheduler") + "/"
	resp, err := e.client.Get(ctx, key, clientv3.WithPrefix())
	if err != nil {
		return nil, err
	}

	stats := make(map[string]int)
	for _, kv := range resp.Kvs {
		parts := path.SplitList(string(kv.Key))
		if len(parts) >= 4 && parts[len(parts)-1] == "task_count" {
			nodeID := parts[len(parts)-2]
			var count int
			fmt.Sscanf(string(kv.Value), "%d", &count)
			stats[nodeID] = count
		}
	}
	return stats, nil
}
