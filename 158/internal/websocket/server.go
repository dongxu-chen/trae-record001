package websocket

import (
	"encoding/json"
	"log"
	"net/http"
	"sync"

	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true
	},
}

type Client struct {
	ID         string
	Conn         *websocket.Conn
	Send         chan []byte
	AuctionID    string
}

type Hub struct {
	clients    map[*Client]bool
	broadcast  chan []byte
	register   chan *Client
	unregister chan *Client
	mu         sync.RWMutex
	auctionClients map[string]map[*Client]bool
}

func NewHub() *Hub {
	return &Hub{
		broadcast:      make(chan []byte),
		register:       make(chan *Client),
		unregister:     make(chan *Client),
		clients:        make(map[*Client]bool),
		auctionClients: make(map[string]map[*Client]bool),
	}
}

func (h *Hub) Run() {
	for {
		select {
		case client := <-h.register:
			h.mu.Lock()
			h.clients[client] = true
			if _, ok := h.auctionClients[client.AuctionID]; !ok {
				h.auctionClients[client.AuctionID] = make(map[*Client]bool)
			}
			h.auctionClients[client.AuctionID][client] = true
			h.mu.Unlock()
			log.Printf("Client %s joined auction %s", client.ID, client.AuctionID)

		case client := <-h.unregister:
			h.mu.Lock()
			if _, ok := h.clients[client]; ok {
				delete(h.clients, client)
				close(client.Send)
				if _, ok := h.auctionClients[client.AuctionID]; ok {
					delete(h.auctionClients[client.AuctionID], client)
				}
			}
			h.mu.Unlock()
			log.Printf("Client %s left auction %s", client.ID, client.AuctionID)

		case message := <-h.broadcast:
			h.mu.RLock()
			for client := range h.clients {
				select {
				case client.Send <- message:
				default:
					close(client.Send)
					delete(h.clients, client)
				}
			}
			h.mu.RUnlock()
		}
	}
}

func (h *Hub) BroadcastToAuction(auctionID string, message []byte) {
	h.mu.RLock()
	defer h.mu.RUnlock()
	
	if clients, ok := h.auctionClients[auctionID]; ok {
		for client := range clients {
			select {
			case client.Send <- message:
			default:
				close(client.Send)
				delete(clients, client)
			}
		}
	}
}

func (h *Hub) BroadcastMessage(message model.Message) {
	data, _ := json.Marshal(message)
	h.broadcast <- data
}

func (h *Hub) BroadcastMessageToAuction(auctionID string, message model.Message) {
	data, _ := json.Marshal(message)
	h.BroadcastToAuction(auctionID, data)
}

func (c *Client) ReadPump(hub *Hub, handler func(*Client, []byte)) {
	defer func() {
		hub.unregister <- c
		c.Conn.Close()
	}()

	for {
		_, message, err := c.Conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("WebSocket error: %v", err)
			}
			break
		}

		handler(c, message)
	}
}

func (c *Client) WritePump() {
	defer c.Conn.Close()
	for message := range c.Send {
		c.Conn.WriteMessage(websocket.TextMessage, message)
	}
}

func ServeWs(hub *Hub, w http.ResponseWriter, r *http.Request, clientID string, auctionID string, messageHandler func(*Client, []byte)) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Println(err)
		return
	}

	client := &Client{
		ID:        clientID,
		Conn:      conn,
		Send:      make(chan []byte, 256),
		AuctionID: auctionID,
	}

	hub.register <- client

	go client.WritePump()
	if messageHandler != nil {
		go client.ReadPump(hub, messageHandler)
	}
}

var GlobalHub = NewHub()

func init() {
	go GlobalHub.Run()
}
