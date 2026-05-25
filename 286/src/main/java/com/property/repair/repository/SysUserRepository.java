package com.property.repair.repository;

import com.property.repair.entity.SysUser;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface SysUserRepository extends JpaRepository<SysUser, Long> {

    SysUser findByUsername(String username);

    List<SysUser> findByRole(String role);
}
