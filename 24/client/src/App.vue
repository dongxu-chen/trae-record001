<template>
  <div class="app">
    <header>
      <h1>Music Streaming</h1>
    </header>
    <main>
      <Playlist />
    </main>
    <Player />
  </div>
</template>

<script setup>
import Player from './components/Player.vue'
import Playlist from './components/Playlist.vue'
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1rem 2rem;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

header h1 {
  margin: 0;
  font-size: 1.8rem;
  font-weight: 600;
}

main {
  flex: 1;
  padding: 2rem;
  padding-bottom: 120px;
}
</style>