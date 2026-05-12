#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameSession.h"
#include "Net/OnlineBlueprintCallProxyBase.h"
#include "Interfaces/OnlineSessionInterface.h"
#include "GameSession.generated.h"

class AVRPawn;

USTRUCT(BlueprintType)
struct FPlayerSessionInfo
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly)
	int32 PlayerId;

	UPROPERTY(BlueprintReadOnly)
	FString PlayerName;

	UPROPERTY(BlueprintReadOnly)
	FTransform LastTransform;

	UPROPERTY(BlueprintReadOnly)
	bool bIsOnline;

	UPROPERTY(BlueprintReadOnly)
	bool bIsMuted;

	UPROPERTY(BlueprintReadOnly)
	float ConnectionLatency;

	UPROPERTY(BlueprintReadOnly)
	TWeakObjectPtr<AVRPawn> Pawn;

	FPlayerSessionInfo()
		: PlayerId(0)
		, PlayerName(TEXT("Unknown"))
		, bIsOnline(false)
		, bIsMuted(false)
		, ConnectionLatency(0.0f)
		, Pawn(nullptr)
	{}
};

UENUM(BlueprintType)
enum class ESessionState : uint8
{
	Offline,
	CreatingSession,
	SessionCreated,
	SearchingSessions,
	SessionsFound,
	JoiningSession,
	SessionJoined,
	DestroyingSession,
	Error
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnSessionStateChanged, ESessionState, NewState);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnPlayerJoined, int32, PlayerId, const FString&, PlayerName);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnPlayerLeft, int32, PlayerId);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnSessionError, const FString&, ErrorMessage, int32, ErrorCode);

UCLASS()
class VRGALLERY_API AVRGalleryGameSession : public AGameSession
{
	GENERATED_BODY()

public:
	AVRGalleryGameSession();

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

public:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Session")
	ESessionState CurrentSessionState;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Session")
	FString SessionName;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Session")
	int32 MaxPlayers;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Session")
	int32 CurrentPlayerCount;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Session")
	bool bIsHost;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Session")
	TMap<int32, FPlayerSessionInfo> ConnectedPlayers;

	UPROPERTY(BlueprintAssignable, Category = "Session Events")
	FOnSessionStateChanged OnSessionStateChanged;

	UPROPERTY(BlueprintAssignable, Category = "Session Events")
	FOnPlayerJoined OnPlayerJoined;

	UPROPERTY(BlueprintAssignable, Category = "Session Events")
	FOnPlayerLeft OnPlayerLeft;

	UPROPERTY(BlueprintAssignable, Category = "Session Events")
	FOnSessionError OnSessionError;

	UFUNCTION(BlueprintCallable, Category = "Session Management")
	void CreateSession(int32 MaxNumPlayers, const FString& InSessionName = TEXT("VRGallerySession"));

	UFUNCTION(BlueprintCallable, Category = "Session Management")
	void SearchSessions(int32 MaxResults = 10);

	UFUNCTION(BlueprintCallable, Category = "Session Management")
	void JoinSession(const FString& InSessionName);

	UFUNCTION(BlueprintCallable, Category = "Session Management")
	void LeaveSession();

	UFUNCTION(BlueprintCallable, Category = "Session Management")
	void DestroySession();

	UFUNCTION(BlueprintCallable, Category = "Player Management")
	void KickPlayer(int32 PlayerId);

	UFUNCTION(BlueprintCallable, Category = "Player Management")
	void MutePlayer(int32 PlayerId, bool bMute);

	UFUNCTION(BlueprintCallable, Category = "Player Management")
	void UpdatePlayerInfo(const FPlayerSessionInfo& PlayerInfo);

	UFUNCTION(BlueprintPure, Category = "Session")
	FPlayerSessionInfo GetPlayerInfo(int32 PlayerId) const;

	UFUNCTION(BlueprintPure, Category = "Session")
	TArray<FPlayerSessionInfo> GetAllPlayers() const;

	UFUNCTION(BlueprintPure, Category = "Session")
	bool IsPlayerConnected(int32 PlayerId) const;

	UFUNCTION(Server, Reliable, WithValidation)
	void Server_NotifyPlayerJoined(int32 PlayerId, const FString& PlayerName);
	void Server_NotifyPlayerJoined_Implementation(int32 PlayerId, const FString& PlayerName);
	bool Server_NotifyPlayerJoined_Validate(int32 PlayerId, const FString& PlayerName);

	UFUNCTION(Server, Reliable, WithValidation)
	void Server_NotifyPlayerLeft(int32 PlayerId);
	void Server_NotifyPlayerLeft_Implementation(int32 PlayerId);
	bool Server_NotifyPlayerLeft_Validate(int32 PlayerId);

	UFUNCTION(NetMulticast, Reliable)
	void Multicast_BroadcastPlayerJoined(int32 PlayerId, const FString& PlayerName);
	void Multicast_BroadcastPlayerJoined_Implementation(int32 PlayerId, const FString& PlayerName);

	UFUNCTION(NetMulticast, Reliable)
	void Multicast_BroadcastPlayerLeft(int32 PlayerId);
	void Multicast_BroadcastPlayerLeft_Implementation(int32 PlayerId);

protected:
	void SetSessionState(ESessionState NewState);
	void HandleCreateSessionComplete(FName InSessionName, bool bWasSuccessful);
	void HandleDestroySessionComplete(FName InSessionName, bool bWasSuccessful);
	void HandleFindSessionsComplete(bool bWasSuccessful);
	void HandleJoinSessionComplete(FName InSessionName, EOnJoinSessionCompleteResult::Type Result);

	UPROPERTY()
	TSharedPtr<class FOnlineSessionSearch> SessionSearch;

	UPROPERTY()
	class AVRGalleryGameMode* GalleryGameMode;

	FTimerHandle ReconnectTimerHandle;

	void TryReconnect();
};
