#include "VoiceChat.h"
#include "TimerManager.h"
#include "Kismet/GameplayStatics.h"

#if WITH_EDITOR
#include "Editor.h"
#endif

UVoiceChat::UVoiceChat()
{
	CurrentState = EVoiceChatState::Disconnected;
	CurrentChannel = TEXT("");
	ServerAddress = TEXT("");
	ServerPort = 5060;
	Domain = TEXT("");
	Username = TEXT("");
	Token = TEXT("");
	MicrophoneVolume = 0.7f;
	SpeakerVolume = 1.0f;
	bPushToTalkEnabled = false;
	bVoiceActivationEnabled = true;
	VoiceActivationThreshold = -40.0f;

	bIsConnected = false;
	bIsInChannel = false;
	bIsLocalMuted = false;
	bIsTalking = false;
	LocalPlayerId = 0;
}

void UVoiceChat::BeginDestroy()
{
	Disconnect();
	Super::BeginDestroy();
}

bool UVoiceChat::Connect()
{
	if (CurrentState == EVoiceChatState::Connecting || CurrentState == EVoiceChatState::Connected)
	{
		return false;
	}

	SetState(EVoiceChatState::Connecting);

	if (Username.IsEmpty())
	{
		Username = FString::Printf(TEXT("Player%d"), FMath::RandRange(1000, 9999));
	}

	LocalPlayerId = GetTypeHash(Username);

	UE_LOG(LogTemp, Log, TEXT("VoiceChat: Connecting to server %s:%d as %s"), *ServerAddress, ServerPort, *Username);

	GetWorld()->GetTimerManager().SetTimerForNextTick(FTimerDelegate::CreateUObject(this, &UVoiceChat::HandleOnLoginComplete, true));

	return true;
}

void UVoiceChat::Disconnect()
{
	CancelReconnect();

	if (bIsInChannel)
	{
		LeaveChannel();
	}

	if (bIsConnected)
	{
		UE_LOG(LogTemp, Log, TEXT("VoiceChat: Disconnecting..."));
		HandleOnLogoutComplete();
	}
}

bool UVoiceChat::JoinChannel(const FString& ChannelName, const FString& ChannelPassword)
{
	if (!bIsConnected)
	{
		NotifyError(TEXT("Not connected to server"));
		return false;
	}

	if (bIsInChannel && CurrentChannel == ChannelName)
	{
		UE_LOG(LogTemp, Warning, TEXT("VoiceChat: Already in channel %s"), *ChannelName);
		return false;
	}

	CurrentChannel = ChannelName;

	UE_LOG(LogTemp, Log, TEXT("VoiceChat: Joining channel %s"), *ChannelName);

	FVoiceChatParticipant LocalParticipant;
	LocalParticipant.PlayerId = LocalPlayerId;
	LocalParticipant.PlayerName = Username;
	LocalParticipant.bIsLocalPlayer = true;
	Participants.Add(LocalPlayerId, LocalParticipant);

	GetWorld()->GetTimerManager().SetTimerForNextTick(FTimerDelegate::CreateUObject(this, &UVoiceChat::HandleOnChannelJoined, ChannelName));

	return true;
}

void UVoiceChat::LeaveChannel()
{
	if (!bIsInChannel)
	{
		return;
	}

	FString LeavingChannel = CurrentChannel;
	CurrentChannel = TEXT("");
	bIsInChannel = false;

	Participants.Empty();

	UE_LOG(LogTemp, Log, TEXT("VoiceChat: Leaving channel %s"), *LeavingChannel);

	OnVoiceChatDisconnected.Broadcast(TEXT("Left channel"));
	HandleOnChannelLeft(LeavingChannel);
}

void UVoiceChat::MuteSelf(bool bMute)
{
	if (bIsLocalMuted == bMute)
	{
		return;
	}

	bIsLocalMuted = bMute;

	if (Participants.Contains(LocalPlayerId))
	{
		Participants[LocalPlayerId].bIsMuted = bMute;
	}

	UE_LOG(LogTemp, Log, TEXT("VoiceChat: Local player %s muted"), bMute ? TEXT("is") : TEXT("is not"));

	OnPlayerMuteStateChanged.Broadcast(LocalPlayerId, bMute);
}

void UVoiceChat::MutePlayer(int32 PlayerId, bool bMute)
{
	if (PlayerId == LocalPlayerId)
	{
		MuteSelf(bMute);
		return;
	}

	if (FVoiceChatParticipant* Participant = Participants.Find(PlayerId))
	{
		Participant->bIsMuted = bMute;
		OnPlayerMuteStateChanged.Broadcast(PlayerId, bMute);
	}
}

void UVoiceChat::SetMicrophoneVolume(float Volume)
{
	MicrophoneVolume = FMath::Clamp(Volume, 0.0f, 2.0f);
	UE_LOG(LogTemp, Log, TEXT("VoiceChat: Microphone volume set to %.2f"), MicrophoneVolume);
}

void UVoiceChat::SetSpeakerVolume(float Volume)
{
	SpeakerVolume = FMath::Clamp(Volume, 0.0f, 2.0f);
	UE_LOG(LogTemp, Log, TEXT("VoiceChat: Speaker volume set to %.2f"), SpeakerVolume);
}

void UVoiceChat::SetPushToTalk(bool bEnabled)
{
	bPushToTalkEnabled = bEnabled;

	if (bEnabled)
	{
		bVoiceActivationEnabled = false;
	}

	UE_LOG(LogTemp, Log, TEXT("VoiceChat: Push-to-talk %s"), bEnabled ? TEXT("enabled") : TEXT("disabled"));
}

void UVoiceChat::SetVoiceActivation(bool bEnabled, float Threshold)
{
	bVoiceActivationEnabled = bEnabled;
	VoiceActivationThreshold = Threshold;

	if (bEnabled)
	{
		bPushToTalkEnabled = false;
	}

	UE_LOG(LogTemp, Log, TEXT("VoiceChat: Voice activation %s, threshold: %.2f"), bEnabled ? TEXT("enabled") : TEXT("disabled"), Threshold);
}

void UVoiceChat::StartTalking()
{
	if (!bPushToTalkEnabled || bIsTalking)
	{
		return;
	}

	bIsTalking = true;

	if (Participants.Contains(LocalPlayerId))
	{
		Participants[LocalPlayerId].bIsSpeaking = true;
	}

	OnPlayerSpeaking.Broadcast(LocalPlayerId, true);
}

void UVoiceChat::StopTalking()
{
	if (!bIsTalking)
	{
		return;
	}

	bIsTalking = false;

	if (Participants.Contains(LocalPlayerId))
	{
		Participants[LocalPlayerId].bIsSpeaking = false;
	}

	OnPlayerSpeaking.Broadcast(LocalPlayerId, false);
}

bool UVoiceChat::IsConnected() const
{
	return bIsConnected;
}

bool UVoiceChat::IsInChannel() const
{
	return bIsInChannel;
}

bool UVoiceChat::IsMuted() const
{
	return bIsLocalMuted;
}

bool UVoiceChat::IsSpeaking() const
{
	return bIsTalking;
}

int32 UVoiceChat::GetParticipantCount() const
{
	return Participants.Num();
}

TArray<FVoiceChatParticipant> UVoiceChat::GetAllParticipants() const
{
	TArray<FVoiceChatParticipant> Result;
	Participants.GenerateValueArray(Result);
	return Result;
}

void UVoiceChat::SetState(EVoiceChatState NewState)
{
	CurrentState = NewState;
}

void UVoiceChat::NotifyError(const FString& ErrorMessage)
{
	UE_LOG(LogTemp, Error, TEXT("VoiceChat Error: %s"), *ErrorMessage);
	SetState(EVoiceChatState::Error);
	OnVoiceChatError.Broadcast(ErrorMessage);
}

void UVoiceChat::HandleOnLoginComplete(bool bSuccess)
{
	if (bSuccess)
	{
		bIsConnected = true;
		SetState(EVoiceChatState::Connected);

		UE_LOG(LogTemp, Log, TEXT("VoiceChat: Connected successfully as %s"), *Username);
		OnVoiceChatConnected.Broadcast(true);
	}
	else
	{
		bIsConnected = false;
		SetState(EVoiceChatState::Disconnected);

		NotifyError(TEXT("Failed to connect to voice chat server"));
		OnVoiceChatConnected.Broadcast(false);
	}
}

void UVoiceChat::HandleOnLogoutComplete()
{
	bIsConnected = false;
	bIsInChannel = false;
	Participants.Empty();

	SetState(EVoiceChatState::Disconnected);

	UE_LOG(LogTemp, Log, TEXT("VoiceChat: Logged out"));
	OnVoiceChatDisconnected.Broadcast(TEXT("Logged out"));
}

void UVoiceChat::HandleOnChannelJoined(const FString& ChannelName)
{
	bIsInChannel = true;

	UE_LOG(LogTemp, Log, TEXT("VoiceChat: Joined channel %s successfully"), *ChannelName);
	OnPlayerJoinedChannel.Broadcast(LocalPlayerId, Username);
}

void UVoiceChat::HandleOnChannelLeft(const FString& ChannelName)
{
	UE_LOG(LogTemp, Log, TEXT("VoiceChat: Left channel %s"), *ChannelName);
	OnPlayerLeftChannel.Broadcast(LocalPlayerId);
}

void UVoiceChat::HandleOnParticipantJoined(int32 ParticipantId, const FString& ParticipantName)
{
	FVoiceChatParticipant NewParticipant;
	NewParticipant.PlayerId = ParticipantId;
	NewParticipant.PlayerName = ParticipantName;
	NewParticipant.bIsLocalPlayer = false;
	NewParticipant.bIsMuted = false;
	NewParticipant.bIsSpeaking = false;
	NewParticipant.Volume = 1.0f;

	Participants.Add(ParticipantId, NewParticipant);

	UE_LOG(LogTemp, Log, TEXT("VoiceChat: Participant %s (ID: %d) joined the channel"), *ParticipantName, ParticipantId);
	OnPlayerJoinedChannel.Broadcast(ParticipantId, ParticipantName);
}

void UVoiceChat::HandleOnParticipantLeft(int32 ParticipantId)
{
	if (Participants.Remove(ParticipantId) > 0)
	{
		UE_LOG(LogTemp, Log, TEXT("VoiceChat: Participant %d left the channel"), ParticipantId);
		OnPlayerLeftChannel.Broadcast(ParticipantId);
	}
}

void UVoiceChat::HandleOnParticipantMuteStateChanged(int32 ParticipantId, bool bIsMuted)
{
	if (FVoiceChatParticipant* Participant = Participants.Find(ParticipantId))
	{
		Participant->bIsMuted = bIsMuted;

		UE_LOG(LogTemp, Log, TEXT("VoiceChat: Participant %d %s muted"), ParticipantId, bIsMuted ? TEXT("is") : TEXT("is not"));
		OnPlayerMuteStateChanged.Broadcast(ParticipantId, bIsMuted);
	}
}

void UVoiceChat::HandleOnParticipantSpeaking(int32 ParticipantId, bool bIsSpeaking)
{
	if (FVoiceChatParticipant* Participant = Participants.Find(ParticipantId))
	{
		Participant->bIsSpeaking = bIsSpeaking;
		OnPlayerSpeaking.Broadcast(ParticipantId, bIsSpeaking);
	}
}

void UVoiceChat::HandleOnAudioStateChanged()
{
	UE_LOG(LogTemp, Log, TEXT("VoiceChat: Audio state changed"));
}

void UVoiceChat::TryReconnect()
{
	if (CurrentState != EVoiceChatState::Error)
	{
		return;
	}

	UE_LOG(LogTemp, Log, TEXT("VoiceChat: Attempting to reconnect..."));
	Connect();
}

void UVoiceChat::CancelReconnect()
{
	if (GetWorld())
	{
		GetWorld()->GetTimerManager().ClearTimer(ReconnectTimerHandle);
	}
}
