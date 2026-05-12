#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "VoiceChat.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnVoiceChatConnected, bool, bSuccess);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnVoiceChatDisconnected, const FString&, Reason);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnVoiceChatError, const FString&, ErrorMessage);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnPlayerJoinedChannel, int32, PlayerId, const FString&, PlayerName);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnPlayerLeftChannel, int32, PlayerId);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnPlayerMuteStateChanged, int32, PlayerId, bool, bIsMuted);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnPlayerSpeaking, int32, PlayerId, bool, bIsSpeaking);

UENUM(BlueprintType)
enum class EVoiceChatState : uint8
{
	Disconnected,
	Connecting,
	Connected,
	Error
};

UENUM(BlueprintType)
enum class EVoiceChatDeviceType : uint8
{
	Input,
	Output,
	Both
};

USTRUCT(BlueprintType)
struct FVoiceChatParticipant
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly)
	int32 PlayerId;

	UPROPERTY(BlueprintReadOnly)
	FString PlayerName;

	UPROPERTY(BlueprintReadOnly)
	bool bIsLocalPlayer;

	UPROPERTY(BlueprintReadOnly)
	bool bIsMuted;

	UPROPERTY(BlueprintReadOnly)
	bool bIsSpeaking;

	UPROPERTY(BlueprintReadOnly)
	float Volume;

	FVoiceChatParticipant()
		: PlayerId(0)
		, PlayerName(TEXT("Unknown"))
		, bIsLocalPlayer(false)
		, bIsMuted(false)
		, bIsSpeaking(false)
		, Volume(1.0f)
	{}
};

UCLASS(Blueprintable, BlueprintType)
class VRGALLERY_API UVoiceChat : public UObject
{
	GENERATED_BODY()

public:
	UVoiceChat();

protected:
	virtual void BeginDestroy() override;

public:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Voice Chat")
	EVoiceChatState CurrentState;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Voice Chat")
	FString CurrentChannel;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Voice Chat")
	TMap<int32, FVoiceChatParticipant> Participants;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voice Chat Settings")
	FString ServerAddress;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voice Chat Settings")
	int32 ServerPort;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voice Chat Settings")
	FString Domain;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voice Chat Settings")
	FString Username;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voice Chat Settings")
	FString Token;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voice Chat Settings")
	float MicrophoneVolume;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voice Chat Settings")
	float SpeakerVolume;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voice Chat Settings")
	bool bPushToTalkEnabled;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voice Chat Settings")
	bool bVoiceActivationEnabled;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Voice Chat Settings")
	float VoiceActivationThreshold;

	UPROPERTY(BlueprintAssignable, Category = "Voice Chat Events")
	FOnVoiceChatConnected OnVoiceChatConnected;

	UPROPERTY(BlueprintAssignable, Category = "Voice Chat Events")
	FOnVoiceChatDisconnected OnVoiceChatDisconnected;

	UPROPERTY(BlueprintAssignable, Category = "Voice Chat Events")
	FOnVoiceChatError OnVoiceChatError;

	UPROPERTY(BlueprintAssignable, Category = "Voice Chat Events")
	FOnPlayerJoinedChannel OnPlayerJoinedChannel;

	UPROPERTY(BlueprintAssignable, Category = "Voice Chat Events")
	FOnPlayerLeftChannel OnPlayerLeftChannel;

	UPROPERTY(BlueprintAssignable, Category = "Voice Chat Events")
	FOnPlayerMuteStateChanged OnPlayerMuteStateChanged;

	UPROPERTY(BlueprintAssignable, Category = "Voice Chat Events")
	FOnPlayerSpeaking OnPlayerSpeaking;

	UFUNCTION(BlueprintCallable, Category = "Voice Chat Management")
	bool Connect();

	UFUNCTION(BlueprintCallable, Category = "Voice Chat Management")
	void Disconnect();

	UFUNCTION(BlueprintCallable, Category = "Voice Chat Management")
	bool JoinChannel(const FString& ChannelName, const FString& ChannelPassword = TEXT(""));

	UFUNCTION(BlueprintCallable, Category = "Voice Chat Management")
	void LeaveChannel();

	UFUNCTION(BlueprintCallable, Category = "Voice Chat Management")
	void MuteSelf(bool bMute);

	UFUNCTION(BlueprintCallable, Category = "Voice Chat Management")
	void MutePlayer(int32 PlayerId, bool bMute);

	UFUNCTION(BlueprintCallable, Category = "Voice Chat Management")
	void SetMicrophoneVolume(float Volume);

	UFUNCTION(BlueprintCallable, Category = "Voice Chat Management")
	void SetSpeakerVolume(float Volume);

	UFUNCTION(BlueprintCallable, Category = "Voice Chat Management")
	void SetPushToTalk(bool bEnabled);

	UFUNCTION(BlueprintCallable, Category = "Voice Chat Management")
	void SetVoiceActivation(bool bEnabled, float Threshold = -40.0f);

	UFUNCTION(BlueprintCallable, Category = "Voice Chat Management")
	void StartTalking();

	UFUNCTION(BlueprintCallable, Category = "Voice Chat Management")
	void StopTalking();

	UFUNCTION(BlueprintPure, Category = "Voice Chat State")
	bool IsConnected() const;

	UFUNCTION(BlueprintPure, Category = "Voice Chat State")
	bool IsInChannel() const;

	UFUNCTION(BlueprintPure, Category = "Voice Chat State")
	bool IsMuted() const;

	UFUNCTION(BlueprintPure, Category = "Voice Chat State")
	bool IsSpeaking() const;

	UFUNCTION(BlueprintPure, Category = "Voice Chat State")
	int32 GetParticipantCount() const;

	UFUNCTION(BlueprintPure, Category = "Voice Chat State")
	TArray<FVoiceChatParticipant> GetAllParticipants() const;

protected:
	void SetState(EVoiceChatState NewState);
	void NotifyError(const FString& ErrorMessage);

	UPROPERTY()
	bool bIsConnected;

	UPROPERTY()
	bool bIsInChannel;

	UPROPERTY()
	bool bIsLocalMuted;

	UPROPERTY()
	bool bIsTalking;

	UPROPERTY()
	int32 LocalPlayerId;

	UFUNCTION()
	void HandleOnLoginComplete(bool bSuccess);

	UFUNCTION()
	void HandleOnLogoutComplete();

	UFUNCTION()
	void HandleOnChannelJoined(const FString& ChannelName);

	UFUNCTION()
	void HandleOnChannelLeft(const FString& ChannelName);

	UFUNCTION()
	void HandleOnParticipantJoined(int32 ParticipantId, const FString& ParticipantName);

	UFUNCTION()
	void HandleOnParticipantLeft(int32 ParticipantId);

	UFUNCTION()
	void HandleOnParticipantMuteStateChanged(int32 ParticipantId, bool bIsMuted);

	UFUNCTION()
	void HandleOnParticipantSpeaking(int32 ParticipantId, bool bIsSpeaking);

	UFUNCTION()
	void HandleOnAudioStateChanged();

	FTimerHandle ReconnectTimerHandle;

	void TryReconnect();
	void CancelReconnect();
};
