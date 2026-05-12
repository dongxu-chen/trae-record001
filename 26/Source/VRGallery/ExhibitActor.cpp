#include "ExhibitActor.h"
#include "Components/StaticMeshComponent.h"
#include "Components/BoxComponent.h"
#include "Components/TextRenderComponent.h"
#include "Components/WidgetComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "MediaPlayer.h"
#include "MediaSoundComponent.h"
#include "MediaTexture.h"
#include "MediaSource.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"
#include "Net/UnrealNetwork.h"
#include "VRPawn.h"

AExhibitActor::AExhibitActor()
{
	PrimaryActorTick.bCanEverTick = true;
	bReplicates = true;
	SetReplicateMovement(true);

	ExhibitMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("ExhibitMesh"));
	RootComponent = ExhibitMesh;
	ExhibitMesh->SetCollisionProfileName(TEXT("BlockAllDynamic"));
	ExhibitMesh->SetIsReplicated(true);

	InteractionCollision = CreateDefaultSubobject<UBoxComponent>(TEXT("InteractionCollision"));
	InteractionCollision->SetupAttachment(ExhibitMesh);
	InteractionCollision->SetCollisionProfileName(TEXT("OverlapAllDynamic"));
	InteractionCollision->SetBoxExtent(FVector(100.0f, 100.0f, 100.0f));
	InteractionCollision->SetIsReplicated(true);

	InfoText = CreateDefaultSubobject<UTextRenderComponent>(TEXT("InfoText"));
	InfoText->SetupAttachment(ExhibitMesh);
	InfoText->SetVisibility(false);
	InfoText->SetRelativeLocation(FVector(0.0f, 0.0f, 150.0f));
	InfoText->SetRelativeRotation(FRotator(0.0f, 180.0f, 0.0f));
	InfoText->HorizontalAlignment = EHTA_Center;

	InfoWidget = CreateDefaultSubobject<UWidgetComponent>(TEXT("InfoWidget"));
	InfoWidget->SetupAttachment(ExhibitMesh);
	InfoWidget->SetVisibility(false);
	InfoWidget->SetRelativeLocation(FVector(0.0f, 0.0f, 200.0f));
	InfoWidget->SetRelativeRotation(FRotator(0.0f, 180.0f, 0.0f));
	InfoWidget->SetDrawSize(FVector2D(400.0f, 300.0f));

	MediaPlayer = CreateDefaultSubobject<UMediaPlayer>(TEXT("MediaPlayer"));
	MediaSoundComponent = CreateDefaultSubobject<UMediaSoundComponent>(TEXT("MediaSoundComponent"));
	MediaSoundComponent->SetupAttachment(ExhibitMesh);

	VideoMediaSource = nullptr;
	AudioSyncThreshold = 0.1f;
	bAutoSyncAudio = true;
	NetworkSyncInterval = 0.1f;

	bIsVideoPlaying = false;
	bIsVideoPlayingReplicated = false;
	LastVideoTime = 0.0f;
	LastNetworkSyncTime = 0.0f;
	InteractingPlayerId = 0;
	ReplicatedVideoTime = 0.0f;

	ExhibitTitle = TEXT("Untitled Exhibit");
	ExhibitDescription = TEXT("No description available.");
	ExhibitArtist = TEXT("Unknown Artist");
	ExhibitYear = 0;

	bCanBeGrabbed = false;
	bShowInfoOnHover = true;

	HoverScaleFactor = 1.05f;
	HoverColor = FLinearColor(1.0f, 1.0f, 0.5f, 1.0f);

	CurrentState = EExhibitState::Inactive;
	bIsInfoVisible = false;
	CurrentInteractor = nullptr;
}

void AExhibitActor::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
	Super::GetLifetimeReplicatedProps(OutLifetimeProps);

	DOREPLIFETIME(AExhibitActor, CurrentState);
	DOREPLIFETIME(AExhibitActor, bIsInfoVisible);
	DOREPLIFETIME(AExhibitActor, InteractingPlayerId);
	DOREPLIFETIME(AExhibitActor, bIsVideoPlayingReplicated);
	DOREPLIFETIME(AExhibitActor, ReplicatedVideoTime);
	DOREPLIFETIME(AExhibitActor, ReplicatedLocation);
	DOREPLIFETIME(AExhibitActor, ReplicatedRotation);
}

void AExhibitActor::BeginPlay()
{
	Super::BeginPlay();

	OriginalScale = GetActorScale3D();

	if (ExhibitMesh)
	{
		if (UMaterialInterface* Material = ExhibitMesh->GetMaterial(0))
		{
			UMaterialInstanceDynamic* MID = ExhibitMesh->CreateAndSetMaterialInstanceDynamic(0);
			if (MID)
			{
				FLinearColor BaseColor;
				if (MID->GetVectorParameterValue(TEXT("BaseColor"), BaseColor))
				{
					OriginalColor = BaseColor;
				}
				else
				{
					OriginalColor = FLinearColor::White;
				}
			}
		}
	}

	if (InfoText)
	{
		InfoText->SetText(FText::FromString(ExhibitTitle));
	}

	if (InteractionCollision)
	{
		InteractionCollision->OnComponentBeginOverlap.AddDynamic(this, &AExhibitActor::OnComponentBeginOverlap);
		InteractionCollision->OnComponentEndOverlap.AddDynamic(this, &AExhibitActor::OnComponentEndOverlap);
	}

	if (MediaPlayer)
	{
		MediaPlayer->OnMediaOpened.AddDynamic(this, &AExhibitActor::OnMediaOpened);
		MediaPlayer->OnMediaClosed.AddDynamic(this, &AExhibitActor::OnMediaClosed);
	}

	if (MediaSoundComponent && MediaPlayer)
	{
		MediaSoundComponent->SetMediaPlayer(MediaPlayer);
	}
}

void AExhibitActor::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	if (HasAuthority())
	{
		if (bAutoSyncAudio && bIsVideoPlaying && MediaPlayer)
		{
			SyncAudioToVideo();
		}

		SyncExhibitStateToClients();
	}
	else
	{
		ApplyRemoteState();
	}
}

void AExhibitActor::SyncExhibitStateToClients()
{
	LastNetworkSyncTime += GetWorld()->GetDeltaSeconds();

	if (LastNetworkSyncTime >= NetworkSyncInterval)
	{
		LastNetworkSyncTime = 0.0f;

		if (CurrentState == EExhibitState::Grabbed)
		{
			ReplicatedLocation = GetActorLocation();
			ReplicatedRotation = GetActorRotation();
		}

		if (bIsVideoPlaying && MediaPlayer)
		{
			FTimespan CurrentTime = MediaPlayer->GetTime();
			ReplicatedVideoTime = CurrentTime.GetTotalSeconds();
		}
	}
}

void AExhibitActor::ApplyRemoteState()
{
	if (CurrentState == EExhibitState::Grabbed && InteractingPlayerId > 0)
	{
		SetActorLocation(FMath::VInterpTo(GetActorLocation(), ReplicatedLocation, GetWorld()->GetDeltaSeconds(), 10.0f));
		SetActorRotation(FMath::RInterpTo(GetActorRotation(), ReplicatedRotation, GetWorld()->GetDeltaSeconds(), 10.0f));
	}
}

void AExhibitActor::OnHoverStart(AVRPawn* Interactor)
{
	if (CurrentState == EExhibitState::Inactive)
	{
		int32 PlayerId = 0;
		if (Interactor)
		{
			PlayerId = Interactor->PlayerId;
		}

		if (HasAuthority())
		{
			CurrentState = EExhibitState::Hovered;
			InteractingPlayerId = PlayerId;
			Multicast_OnExhibitStateChanged(EExhibitState::Hovered, PlayerId);
		}
		else if (PlayerId > 0)
		{
			Server_SetExhibitState(EExhibitState::Hovered, PlayerId);
		}

		CurrentInteractor = Interactor;

		SetActorScale3D(OriginalScale * HoverScaleFactor);

		if (ExhibitMesh)
		{
			if (UMaterialInstanceDynamic* MID = Cast<UMaterialInstanceDynamic>(ExhibitMesh->GetMaterial(0)))
			{
				MID->SetVectorParameterValue(TEXT("BaseColor"), HoverColor);
			}
		}

		if (bShowInfoOnHover)
		{
			ShowInfo();
		}

		OnExhibitHovered();
	}
}

void AExhibitActor::OnHoverEnd(AVRPawn* Interactor)
{
	if (CurrentState == EExhibitState::Hovered && CurrentInteractor == Interactor)
	{
		CurrentState = EExhibitState::Inactive;
		CurrentInteractor = nullptr;

		SetActorScale3D(OriginalScale);

		if (ExhibitMesh)
		{
			if (UMaterialInstanceDynamic* MID = Cast<UMaterialInstanceDynamic>(ExhibitMesh->GetMaterial(0)))
			{
				MID->SetVectorParameterValue(TEXT("BaseColor"), OriginalColor);
			}
		}

		if (bShowInfoOnHover)
		{
			HideInfo();
		}

		OnExhibitUnhovered();
	}
}

void AExhibitActor::OnSelect(AVRPawn* Interactor)
{
	if (CurrentState == EExhibitState::Hovered || CurrentState == EExhibitState::Inactive)
	{
		CurrentState = EExhibitState::Selected;
		CurrentInteractor = Interactor;

		ShowInfo();
		OnExhibitSelected();
	}
	else if (CurrentState == EExhibitState::Selected)
	{
		OnDeselect(Interactor);
	}
}

void AExhibitActor::OnDeselect(AVRPawn* Interactor)
{
	if (CurrentState == EExhibitState::Selected && CurrentInteractor == Interactor)
	{
		CurrentState = EExhibitState::Inactive;
		CurrentInteractor = nullptr;

		HideInfo();
		OnExhibitDeselected();
	}
}

void AExhibitActor::OnGrab(AVRPawn* Interactor)
{
	if (bCanBeGrabbed && (CurrentState == EExhibitState::Hovered || CurrentState == EExhibitState::Selected || CurrentState == EExhibitState::Inactive))
	{
		CurrentState = EExhibitState::Grabbed;
		CurrentInteractor = Interactor;
	}
}

void AExhibitActor::OnRelease(AVRPawn* Interactor)
{
	if (CurrentState == EExhibitState::Grabbed && CurrentInteractor == Interactor)
	{
		CurrentState = EExhibitState::Inactive;
		CurrentInteractor = nullptr;
	}
}

void AExhibitActor::ShowInfo()
{
	bIsInfoVisible = true;

	if (InfoText)
	{
		InfoText->SetVisibility(true);
	}

	if (InfoWidget)
	{
		InfoWidget->SetVisibility(true);
	}
}

void AExhibitActor::HideInfo()
{
	bIsInfoVisible = false;

	if (InfoText)
	{
		InfoText->SetVisibility(false);
	}

	if (InfoWidget)
	{
		InfoWidget->SetVisibility(false);
	}
}

void AExhibitActor::OnComponentBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	if (AVRPawn* Pawn = Cast<AVRPawn>(OtherActor))
	{
		OnHoverStart(Pawn);
	}
}

void AExhibitActor::OnComponentEndOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex)
{
	if (AVRPawn* Pawn = Cast<AVRPawn>(OtherActor))
	{
		OnHoverEnd(Pawn);
	}
}

void AExhibitActor::PlayVideo()
{
	if (!MediaPlayer || !VideoMediaSource) return;

	MediaPlayer->OpenSource(VideoMediaSource);
	bIsVideoPlaying = true;
	LastVideoTime = 0.0f;

	if (bAutoSyncAudio)
	{
		GetWorldTimerManager().SetTimer(
			SyncTimerHandle,
			this,
			&AExhibitActor::SyncAudioToVideo,
			0.1f,
			true
		);
	}
}

void AExhibitActor::PauseVideo()
{
	if (!MediaPlayer) return;

	MediaPlayer->Pause();
	bIsVideoPlaying = false;

	if (SyncTimerHandle.IsValid())
	{
		GetWorldTimerManager().ClearTimer(SyncTimerHandle);
	}
}

void AExhibitActor::StopVideo()
{
	if (!MediaPlayer) return;

	MediaPlayer->Close();
	bIsVideoPlaying = false;
	LastVideoTime = 0.0f;

	if (SyncTimerHandle.IsValid())
	{
		GetWorldTimerManager().ClearTimer(SyncTimerHandle);
	}
}

void AExhibitActor::SyncAudioToVideo()
{
	if (!MediaPlayer) return;

	if (!MediaPlayer->IsPlaying())
	{
		return;
	}

	FTimespan CurrentTime = MediaPlayer->GetTime();
	float CurrentSeconds = CurrentTime.GetTotalSeconds();

	FTimespan VideoDuration = MediaPlayer->GetDuration();
	float TotalSeconds = VideoDuration.GetTotalSeconds();

	if (TotalSeconds <= 0.0f)
	{
		return;
	}

	float VideoProgress = CurrentSeconds / TotalSeconds;

	float TimeDiff = FMath::Abs(CurrentSeconds - LastVideoTime);

	if (TimeDiff > AudioSyncThreshold && TimeDiff < 1.0f)
	{
		if (MediaSoundComponent)
		{
			MediaSoundComponent->SetPitchMultiplier(1.0f);
		}
	}
	else if (TimeDiff >= 1.0f)
	{
		if (CurrentSeconds > LastVideoTime)
		{
			MediaPlayer->Seek(FTimespan::FromSeconds(LastVideoTime));
		}
	}

	LastVideoTime = CurrentSeconds;
}

bool AExhibitActor::IsVideoPlaying() const
{
	return bIsVideoPlaying && MediaPlayer && MediaPlayer->IsPlaying();
}

void AExhibitActor::OnMediaOpened(FString OpenedUrl)
{
	if (MediaPlayer)
	{
		MediaPlayer->Play();
	}
}

void AExhibitActor::OnMediaClosed()
{
	bIsVideoPlaying = false;
	bIsVideoPlayingReplicated = false;
}

void AExhibitActor::OnRep_CurrentState()
{
	switch (CurrentState)
	{
	case EExhibitState::Hovered:
		SetActorScale3D(OriginalScale * HoverScaleFactor);
		if (ExhibitMesh)
		{
			if (UMaterialInstanceDynamic* MID = Cast<UMaterialInstanceDynamic>(ExhibitMesh->GetMaterial(0)))
			{
				MID->SetVectorParameterValue(TEXT("BaseColor"), HoverColor);
			}
		}
		OnExhibitHovered();
		break;

	case EExhibitState::Selected:
		OnExhibitSelected();
		break;

	case EExhibitState::Grabbed:
		OnExhibitSelected();
		break;

	case EExhibitState::Inactive:
	default:
		SetActorScale3D(OriginalScale);
		if (ExhibitMesh)
		{
			if (UMaterialInstanceDynamic* MID = Cast<UMaterialInstanceDynamic>(ExhibitMesh->GetMaterial(0)))
			{
				MID->SetVectorParameterValue(TEXT("BaseColor"), OriginalColor);
			}
		}
		OnExhibitUnhovered();
		break;
	}
}

void AExhibitActor::OnRep_InfoVisible()
{
	if (InfoText)
	{
		InfoText->SetVisibility(bIsInfoVisible);
	}
	if (InfoWidget)
	{
		InfoWidget->SetVisibility(bIsInfoVisible);
	}
}

void AExhibitActor::OnRep_VideoState()
{
	if (!HasAuthority() && MediaPlayer)
	{
		if (bIsVideoPlayingReplicated)
		{
			if (!MediaPlayer->IsPlaying())
			{
				MediaPlayer->Seek(FTimespan::FromSeconds(ReplicatedVideoTime));
				if (VideoMediaSource)
				{
					MediaPlayer->OpenSource(VideoMediaSource);
				}
			}
		}
		else
		{
			MediaPlayer->Pause();
		}
	}
}

void AExhibitActor::Server_SetExhibitState_Implementation(EExhibitState NewState, int32 PlayerId)
{
	CurrentState = NewState;
	InteractingPlayerId = PlayerId;
	Multicast_OnExhibitStateChanged(NewState, PlayerId);
}

bool AExhibitActor::Server_SetExhibitState_Validate(EExhibitState NewState, int32 PlayerId)
{
	return true;
}

void AExhibitActor::Server_PlayVideo_Implementation(int32 PlayerId)
{
	PlayVideo();
	bIsVideoPlayingReplicated = true;
	Multicast_OnVideoStateChanged(true, ReplicatedVideoTime);
}

bool AExhibitActor::Server_PlayVideo_Validate(int32 PlayerId)
{
	return true;
}

void AExhibitActor::Server_PauseVideo_Implementation(int32 PlayerId)
{
	PauseVideo();
	bIsVideoPlayingReplicated = false;
	Multicast_OnVideoStateChanged(false, ReplicatedVideoTime);
}

bool AExhibitActor::Server_PauseVideo_Validate(int32 PlayerId)
{
	return true;
}

void AExhibitActor::Server_StopVideo_Implementation(int32 PlayerId)
{
	StopVideo();
	bIsVideoPlayingReplicated = false;
	Multicast_OnVideoStateChanged(false, 0.0f);
}

bool AExhibitActor::Server_StopVideo_Validate(int32 PlayerId)
{
	return true;
}

void AExhibitActor::Server_UpdateTransform_Implementation(const FVector& Location, const FRotator& Rotation)
{
	ReplicatedLocation = Location;
	ReplicatedRotation = Rotation;
}

bool AExhibitActor::Server_UpdateTransform_Validate(const FVector& Location, const FRotator& Rotation)
{
	return true;
}

void AExhibitActor::Multicast_OnExhibitStateChanged_Implementation(EExhibitState NewState, int32 PlayerId)
{
	OnRep_CurrentState();
}

void AExhibitActor::Multicast_OnVideoStateChanged_Implementation(bool bPlaying, float Time)
{
	ReplicatedVideoTime = Time;
	OnRep_VideoState();
}
