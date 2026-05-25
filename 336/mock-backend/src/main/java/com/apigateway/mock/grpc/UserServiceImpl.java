package com.apigateway.mock.grpc;

import com.apigateway.grpc.user.*;
import com.apigateway.mock.common.MockService;
import com.apigateway.mock.entity.User;
import com.apigateway.mock.store.UserStore;
import io.grpc.stub.StreamObserver;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class UserServiceImpl extends UserServiceGrpc.UserServiceImplBase {

    private final UserStore userStore;
    private final MockService mockService;
    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    @Override
    public void getUser(GetUserRequest request, StreamObserver<UserResponse> responseObserver) {
        log.info("gRPC查询用户: id={}", request.getId());
        mockService.simulate();

        User user = userStore.findById(request.getId());
        if (user == null) {
            responseObserver.onError(new RuntimeException("用户不存在"));
            return;
        }

        UserResponse response = convertToUserResponse(user);
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void listUsers(ListUsersRequest request, StreamObserver<ListUsersResponse> responseObserver) {
        log.info("gRPC查询用户列表: page={}, size={}", request.getPage(), request.getSize());
        mockService.simulate();

        List<User> users = new ArrayList<>(userStore.findAll());
        users.sort(Comparator.comparing(User::getId));

        int page = request.getPage();
        int size = request.getSize();
        int start = (page - 1) * size;
        int end = Math.min(start + size, users.size());
        List<User> pageUsers;
        if (start >= users.size()) {
            pageUsers = new ArrayList<>();
        } else {
            pageUsers = users.subList(start, end);
        }

        List<UserResponse> userResponses = pageUsers.stream()
                .map(this::convertToUserResponse)
                .toList();

        ListUsersResponse response = ListUsersResponse.newBuilder()
                .addAllUsers(userResponses)
                .setTotal(users.size())
                .setPage(page)
                .setSize(size)
                .build();

        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void createUser(CreateUserRequest request, StreamObserver<UserResponse> responseObserver) {
        log.info("gRPC创建用户: name={}, email={}", request.getName(), request.getEmail());
        mockService.simulate();

        User user = User.builder()
                .name(request.getName())
                .email(request.getEmail())
                .age(request.getAge())
                .build();

        User saved = userStore.save(user);
        UserResponse response = convertToUserResponse(saved);
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void updateUser(UpdateUserRequest request, StreamObserver<UserResponse> responseObserver) {
        log.info("gRPC更新用户: id={}", request.getId());
        mockService.simulate();

        if (!userStore.existsById(request.getId())) {
            responseObserver.onError(new RuntimeException("用户不存在"));
            return;
        }

        User user = User.builder()
                .id(request.getId())
                .name(request.getName())
                .email(request.getEmail())
                .age(request.getAge())
                .build();

        User saved = userStore.save(user);
        UserResponse response = convertToUserResponse(saved);
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void deleteUser(DeleteUserRequest request, StreamObserver<DeleteUserResponse> responseObserver) {
        log.info("gRPC删除用户: id={}", request.getId());
        mockService.simulate();

        boolean deleted = userStore.deleteById(request.getId());
        DeleteUserResponse response = DeleteUserResponse.newBuilder()
                .setSuccess(deleted)
                .setMessage(deleted ? "删除成功" : "用户不存在")
                .build();

        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    private UserResponse convertToUserResponse(User user) {
        return UserResponse.newBuilder()
                .setId(user.getId())
                .setName(user.getName())
                .setEmail(user.getEmail())
                .setAge(user.getAge())
                .setCreatedAt(user.getCreatedAt() != null ? user.getCreatedAt().format(FORMATTER) : "")
                .setUpdatedAt(user.getUpdatedAt() != null ? user.getUpdatedAt().format(FORMATTER) : "")
                .build();
    }
}
