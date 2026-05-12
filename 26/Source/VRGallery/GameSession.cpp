#include "GameSession.h"
#include "VRGalleryGameMode.h"
#include "VRPawn.h"
#include "OnlineSubsystem.h"
#include "OnlineSessionSettings.h"
#include "Online/OnlineSessionNames.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"

AVRGalleryGameSession::AVRGalleryGameSession()
{
	CurrentSessionState = ESessionState::Offline;
	SessionName = TEXT("VRGallerySession");
	MaxPlayers = 10;
	CurrentPlayerCount = 0;
	bIsHost = false;

	PrimaryActorTick.bCanEverTick = false;
}

void AVRGalleryGameSession::BeginPlay()
{
	Super::BeginPlay();

	GalleryGameMode = Cast<AVRGalleryGameMode>(UGameplayStatics::GetGameMode(this));

	if (IOnlineSubsystem* OnlineSub = IOnlineSubsystem::Get())
	{
		IOnlineSessionPtr SessionInterface = OnlineSub->GetSessionInterface();
		if (SessionInterface.IsValid())
		{
			SessionInterface->AddOnCreateSessionCompleteDelegate_Handle(FOnCreateSessionCompleteDelegate::CreateUObject(
				this, &AVRGalleryGameSession::HandleCreateSessionComplete));
			SessionInterface->AddOnDestroySessionCompleteDelegate_Handle(FOnDestroySessionCompleteDelegate::CreateUObject(
				this, &AVRGalleryGameSession::HandleDestroySessionComplete));
			SessionInterface->AddOnFindSessionsCompleteDelegate_Handle(FOnFindSessionsCompleteDelegate::CreateUObject(
				this, &AVRGalleryGameSession::HandleFindSessionsComplete));
			SessionInterface->AddOnJoinSessionCompleteDelegate_Handle(FOnJoinSessionCompleteDelegate::CreateUObject(
				this, &AVRGalleryGameSession::HandleJoinSessionComplete));
		}
	}
}

void AVRGalleryGameSession::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	Super::EndPlay(EndPlayReason);

	if (CurrentSessionState == ESessionState::SessionCreated || CurrentSessionState == ESessionState::SessionJoined)
	{
		DestroySession();
	}

	if (IOnlineSubsystem* OnlineSub = IOnlineSubsystem::Get())
	{
		IOnlineSessionPtr SessionInterface = OnlineSub->GetSessionInterface();
		if (SessionInterface.IsValid())
		{
			SessionInterface->ClearOnCreateSessionCompleteDelegates(this);
			SessionInterface->ClearOnDestroySessionCompleteDelegates(this);
			SessionInterface->ClearOnFindSessionsCompleteDelegates(this);
			SessionInterface->ClearOnJoinSessionCompleteDelegates(this);
		}
	}
}

void AVRGalleryGameSession::SetSessionState(ESessionState NewState)
{
	CurrentSessionState = NewState;
	OnSessionStateChanged.Broadcast(NewState);
}

void AVRGalleryGameSession::CreateSession(int32 MaxNumPlayers, const FString& InSessionName)
{
	SetSessionState(ESessionState::CreatingSession);

	MaxPlayers = MaxNumPlayers;
	SessionName = InSessionName;
	bIsHost = true;

	IOnlineSubsystem* OnlineSub = IOnlineSubsystem::Get();
	if (!OnlineSub)
	{
		SetSessionState(ESessionState::Error);
		OnSessionError.Broadcast(TEXT("Online Subsystem not available"), -1);
		return;
	}

	IOnlineSessionPtr SessionInterface = OnlineSub->GetSessionInterface();
	if (!SessionInterface.IsValid())
	{
		SetSessionState(ESessionState::Error);
		OnSessionError.Broadcast(TEXT("Session Interface not available"), -2);
		return;
	}

	FOnlineSessionSettings SessionSettings;
	SessionSettings.bIsLANMatch = true;
	SessionSettings.NumPublicConnections = MaxPlayers;
	SessionSettings.NumPrivateConnections = 0;
	SessionSettings.bAllowInvites = true;
	SessionSettings.bAllowJoinInProgress = true;
	SessionSettings.bAllowJoinViaPresence = true;
	SessionSettings.bUsesPresence = true;
	SessionSettings.bUseLobbiesIfAvailable = true;
	SessionSettings.bShouldAdvertise = true;
	SessionSettings.Settings.Add(SETTING_MAPNAME, FOnlineSessionSetting(FString(TEXT("GalleryMap")), EOnlineDataAdvertisementType::ViaOnlineService));

	SessionInterface->CreateSession(0, FName(*InSessionName), SessionSettings);
}

void AVRGalleryGameSession::SearchSessions(int32 MaxResults)
{
	SetSessionState(ESessionState::SearchingSessions);

	IOnlineSubsystem* OnlineSub = IOnlineSubsystem::Get();
	if (!OnlineSub)
	{
		SetSessionState(ESessionState::Error);
		OnSessionError.Broadcast(TEXT("Online Subsystem not available"), -1);
		return;
	}

	IOnlineSessionPtr SessionInterface = OnlineSub->GetSessionInterface();
	if (!SessionInterface.IsValid())
	{
		SetSessionState(ESessionState::Error);
		OnSessionError.Broadcast(TEXT("Session Interface not available"), -2);
		return;
	}

	SessionSearch = MakeShareable(new FOnlineSessionSearch());
	SessionSearch->bIsLanQuery = true;
	SessionSearch->MaxSearchResults = MaxResults;
	SessionSearch->QuerySettings.Set(SEARCH_PRESENCE, true, EOnlineComparisonOp::Equals);

	SessionInterface->FindSessions(0, SessionSearch.ToSharedRef());
}

void AVRGalleryGameSession::JoinSession(const FString& InSessionName)
{
	SetSessionState(ESessionState::JoiningSession);

	bIsHost = false;
	SessionName = InSessionName;

	IOnlineSubsystem* OnlineSub = IOnlineSubsystem::Get();
	if (!OnlineSub)
	{
		SetSessionState(ESessionState::Error);
		OnSessionError.Broadcast(TEXT("Online Subsystem not available"), -1);
		return;
	}

	IOnlineSessionPtr SessionInterface = OnlineSub->GetSessionInterface();
	if (!SessionInterface.IsValid())
	{
		SetSessionState(ESessionState::Error);
		OnSessionError.Broadcast(TEXT("Session Interface not available"), -2);
		return;
	}

	if (SessionSearch.IsValid() && SessionSearch->SearchResults.Num() > 0)
	{
		SessionInterface->JoinSession(0, FName(*InSessionName), SessionSearch->SearchResults[0]);
	}
	else
	{
		SetSessionState(ESessionState::Error);
		OnSessionError.Broadcast(TEXT("No sessions found to join"), -3);
	}
}

void AVRGalleryGameSession::LeaveSession()
{
	DestroySession();
}

void AVRGalleryGameSession::DestroySession()
{
	SetSessionState(ESessionState::DestroyingSession);

	IOnlineSubsystem* OnlineSub = IOnlineSubsystem::Get();
	if (!OnlineSub)
	{
		SetSessionState(ESessionState::Offline);
		return;
	}

	IOnlineSessionPtr SessionInterface = OnlineSub->GetSessionInterface();
	if (SessionInterface.IsValid())
	{
		SessionInterface->DestroySession(FName(*SessionName));
	}
	else
	{
		SetSessionState(ESessionState::Offline);
	}
}

void AVRGalleryGameSession::KickPlayer(int32 PlayerId)
{
	if (!HasAuthority()) return;

	if (FPlayerSessionInfo* PlayerInfo = ConnectedPlayers.Find(PlayerId))
	{
		ConnectedPlayers.Remove(PlayerId);
		CurrentPlayerCount--;
		Multicast_BroadcastPlayerLeft(PlayerId);
		OnPlayerLeft.Broadcast(PlayerId);
	}
}

void AVRGalleryGameSession::MutePlayer(int32 PlayerId, bool bMute)
{
	if (!HasAuthority()) return;

	if (FPlayerSessionInfo* PlayerInfo = ConnectedPlayers.Find(PlayerId))
	{
		PlayerInfo->bIsMuted = bMute;
	}
}

void AVRGalleryGameSession::UpdatePlayerInfo(const FPlayerSessionInfo& PlayerInfo)
{
	if (FPlayerSessionInfo* ExistingInfo = ConnectedPlayers.Find(PlayerInfo.PlayerId))
	{
		ExistingInfo->PlayerName = PlayerInfo.PlayerName;
		ExistingInfo->LastTransform = PlayerInfo.LastTransform;
		ExistingInfo->bIsOnline = PlayerInfo.bIsOnline;
		ExistingInfo->ConnectionLatency = PlayerInfo.ConnectionLatency;
		ExistingInfo->Pawn = PlayerInfo.Pawn;
	}
}

FPlayerSessionInfo AVRGalleryGameSession::GetPlayerInfo(int32 PlayerId) const
{
	if (const FPlayerSessionInfo* PlayerInfo = ConnectedPlayers.Find(PlayerId))
	{
		return *PlayerInfo;
	}
	return FPlayerSessionInfo();
}

TArray<FPlayerSessionInfo> AVRGalleryGameSession::GetAllPlayers() const
{
	TArray<FPlayerSessionInfo> Players;
	ConnectedPlayers.GenerateValueArray(Players);
	return Players;
}

bool AVRGalleryGameSession::IsPlayerConnected(int32 PlayerId) const
{
	if (const FPlayerSessionInfo* PlayerInfo = ConnectedPlayers.Find(PlayerId))
	{
		return PlayerInfo->bIsOnline;
	}
	return false;
}

void AVRGalleryGameSession::Server_NotifyPlayerJoined_Implementation(int32 PlayerId, const FString& PlayerName)
{
	FPlayerSessionInfo PlayerInfo;
	PlayerInfo.PlayerId = PlayerId;
	PlayerInfo.PlayerName = PlayerName;
	PlayerInfo.bIsOnline = true;
	PlayerInfo.bIsMuted = false;

	ConnectedPlayers.Add(PlayerId, PlayerInfo);
	CurrentPlayerCount = ConnectedPlayers.Num();

	Multicast_BroadcastPlayerJoined(PlayerId, PlayerName);
}

bool AVRGalleryGameSession::Server_NotifyPlayerJoined_Validate(int32 PlayerId, const FString& PlayerName)
{
	return PlayerId > 0 && PlayerName.Len() > 0;
}

void AVRGalleryGameSession::Server_NotifyPlayerLeft_Implementation(int32 PlayerId)
{
	ConnectedPlayers.Remove(PlayerId);
	CurrentPlayerCount = ConnectedPlayers.Num();
	Multicast_BroadcastPlayerLeft(PlayerId);
}

bool AVRGalleryGameSession::Server_NotifyPlayerLeft_Validate(int32 PlayerId)
{
	return true;
}

void AVRGalleryGameSession::Multicast_BroadcastPlayerJoined_Implementation(int32 PlayerId, const FString& PlayerName)
{
	OnPlayerJoined.Broadcast(PlayerId, PlayerName);
}

void AVRGalleryGameSession::Multicast_BroadcastPlayerLeft_Implementation(int32 PlayerId)
{
	OnPlayerLeft.Broadcast(PlayerId);
}

void AVRGalleryGameSession::HandleCreateSessionComplete(FName InSessionName, bool bWasSuccessful)
{
	if (bWasSuccessful)
	{
		SetSessionState(ESessionState::SessionCreated);
	}
	else
	{
		SetSessionState(ESessionState::Error);
		OnSessionError.Broadcast(TEXT("Failed to create session"), 1);
	}
}

void AVRGalleryGameSession::HandleDestroySessionComplete(FName InSessionName, bool bWasSuccessful)
{
	SetSessionState(ESessionState::Offline);
	ConnectedPlayers.Empty();
	CurrentPlayerCount = 0;
	bIsHost = false;
}

void AVRGalleryGameSession::HandleFindSessionsComplete(bool bWasSuccessful)
{
	if (bWasSuccessful && SessionSearch.IsValid() && SessionSearch->SearchResults.Num() > 0)
	{
		SetSessionState(ESessionState::SessionsFound);
	}
	else
	{
		SetSessionState(ESessionState::Error);
		OnSessionError.Broadcast(TEXT("No sessions found"), 2);
	}
}

void AVRGalleryGameSession::HandleJoinSessionComplete(FName InSessionName, EOnJoinSessionCompleteResult::Type Result)
{
	if (Result == EOnJoinSessionCompleteResult::Success)
	{
		SetSessionState(ESessionState::SessionJoined);
	}
	else
	{
		SetSessionState(ESessionState::Error);
		FString ErrorMsg;
		switch (Result)
		{
		case EOnJoinSessionCompleteResult::SessionIsFull:
			ErrorMsg = TEXT("Session is full");
			break;
		case EOnJoinSessionCompleteResult::SessionDoesNotExist:
			ErrorMsg = TEXT("Session does not exist");
			break;
		case EOnJoinSessionCompleteResult::CouldNotRetrieveAddress:
			ErrorMsg = TEXT("Could not retrieve session address");
			break;
		case EOnJoinSessionCompleteResult::AlreadyInSession:
			ErrorMsg = TEXT("Already in session");
			break;
		default:
			ErrorMsg = TEXT("Unknown error");
			break;
		}
		OnSessionError.Broadcast(ErrorMsg, static_cast<int32>(Result));
	}
}

void AVRGalleryGameSession::TryReconnect()
{
	if (CurrentSessionState == ESessionState::Error)
	{
		SetSessionState(ESessionState::SearchingSessions);
	}
}
