package com.checkin.repository;

import com.checkin.entity.CheckinReminder;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface CheckinReminderRepository extends JpaRepository<CheckinReminder, Long> {
    List<CheckinReminder> findByUserId(Long userId);
    Optional<CheckinReminder> findByUserIdAndReminderType(Long userId, String reminderType);
    List<CheckinReminder> findByEnabledTrue();
}
