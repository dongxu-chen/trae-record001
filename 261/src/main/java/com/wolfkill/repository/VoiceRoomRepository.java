package com.wolfkill.repository;

import com.wolfkill.entity.VoiceRoom;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface VoiceRoomRepository extends JpaRepository<VoiceRoom, Long> {
    Optional<VoiceRoom> findByRoomIdAndRoomType(Long roomId, String roomType);
    Optional<VoiceRoom> findByVoiceRoomId(String voiceRoomId);
    List<VoiceRoom> findByRoomId(Long roomId);
    List<VoiceRoom> findByActiveTrue();
}
