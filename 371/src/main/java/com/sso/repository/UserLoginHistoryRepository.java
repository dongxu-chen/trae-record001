package com.sso.repository;

import com.sso.entity.UserLoginHistory;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface UserLoginHistoryRepository extends JpaRepository<UserLoginHistory, Long> {

    List<UserLoginHistory> findByUsernameOrderByLoginTimeDesc(String username);

    List<UserLoginHistory> findByUsernameAndLoginTimeAfterOrderByLoginTimeDesc(
            String username, LocalDateTime after);

    List<UserLoginHistory> findByIpAddressAndLoginTimeAfterOrderByLoginTimeDesc(
            String ipAddress, LocalDateTime after);

    long countByUsernameAndSuccessAndLoginTimeAfter(
            String username, boolean success, LocalDateTime after);
}
