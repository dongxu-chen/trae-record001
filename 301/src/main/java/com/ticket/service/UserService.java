package com.ticket.service;

import com.ticket.entity.User;
import com.ticket.exception.BusinessException;
import com.ticket.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class UserService {

    private final UserRepository userRepository;

    @Transactional
    public User createUser(User user) {
        userRepository.findByUsername(user.getUsername()).ifPresent(u -> {
            throw new BusinessException("用户名已存在: " + user.getUsername());
        });
        user.setPassword("{noop}" + user.getPassword());
        return userRepository.save(user);
    }

    @Transactional
    public User updateUser(Long id, User user) {
        User existing = getUserById(id);
        if (!existing.getUsername().equals(user.getUsername())) {
            userRepository.findByUsername(user.getUsername()).ifPresent(u -> {
                if (!u.getId().equals(id)) {
                    throw new BusinessException("用户名已存在: " + user.getUsername());
                }
            });
        }
        existing.setUsername(user.getUsername());
        existing.setRealName(user.getRealName());
        existing.setEmail(user.getEmail());
        existing.setPhone(user.getPhone());
        existing.setDepartment(user.getDepartment());
        existing.setPosition(user.getPosition());
        existing.setAvailable(user.getAvailable());
        return userRepository.save(existing);
    }

    @Transactional
    public void deleteUser(Long id) {
        User user = getUserById(id);
        userRepository.delete(user);
        log.info("用户已删除: {}", id);
    }

    public User getUserById(Long id) {
        return userRepository.findById(id)
                .orElseThrow(() -> new BusinessException("用户不存在: " + id));
    }

    public User getUserByUsername(String username) {
        return userRepository.findByUsername(username)
                .orElseThrow(() -> new BusinessException("用户不存在: " + username));
    }

    public Page<User> getUserList(Pageable pageable) {
        return userRepository.findAll(pageable);
    }

    public List<User> getAvailableUsers() {
        return userRepository.findByAvailableTrue();
    }

    public List<User> getAvailableUsersByDepartment(String department) {
        return userRepository.findByDepartmentAndAvailableTrue(department);
    }

    @Transactional
    public User toggleStatus(Long id) {
        User user = getUserById(id);
        user.setAvailable(!user.getAvailable());
        return userRepository.save(user);
    }
}
