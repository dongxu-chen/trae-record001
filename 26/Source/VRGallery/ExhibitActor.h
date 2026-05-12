#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Net/UnrealNetwork.h"
#include "ExhibitActor.generated.h"

class UStaticMeshComponent;
class UBoxComponent;
class UTextRenderComponent;
class UWidgetComponent;
class UMediaPlayer;
class UMediaSoundComponent;
class UMediaTexture;
class AVRPawn;

UENUM(BlueprintType)
enum class EExhibitState : uint8
{
	Inactive,
	Hovered,
	Selected,
	Grabbed
};

UCLASS()
class VRGALLERY_API AExhibitActor : public AActor
{
	GENERATED_BODY()

public:
	AExhibitActor();

	virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

protected:
	virtual void BeginPlay() override;

public:
	virtual void Tick(float DeltaTime) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Exhibit")
	UStaticMeshComponent* ExhibitMesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Exhibit")
	UBoxComponent* InteractionCollision;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Exhibit")
	UTextRenderComponent* InfoText;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Exhibit")
	UWidgetComponent* InfoWidget;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Exhibit Media")
	UMediaPlayer* MediaPlayer;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Exhibit Media")
	UMediaSoundComponent* MediaSoundComponent;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Exhibit Media")
	UMediaTexture* MediaTexture;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Exhibit Media")
	class UMediaSource* VideoMediaSource;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Exhibit Media")
	float AudioSyncThreshold;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Exhibit Media")
	bool bAutoSyncAudio;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Exhibit Info")
	FString ExhibitTitle;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Exhibit Info")
	FString ExhibitDescription;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Exhibit Info")
	FString ExhibitArtist;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Exhibit Info")
	int32 ExhibitYear;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Exhibit Settings")
	bool bCanBeGrabbed;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Exhibit Settings")
	bool bShowInfoOnHover;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Exhibit Effects")
	float HoverScaleFactor;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Exhibit Effects")
	FLinearColor HoverColor;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, ReplicatedUsing = OnRep_CurrentState, Category = "Exhibit State")
	EExhibitState CurrentState;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, ReplicatedUsing = OnRep_InfoVisible, Category = "Exhibit State")
	bool bIsInfoVisible;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Replicated, Category = "Exhibit Network")
	int32 InteractingPlayerId;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, ReplicatedUsing = OnRep_VideoState, Category = "Exhibit Network")
	bool bIsVideoPlayingReplicated;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Replicated, Category = "Exhibit Network")
	float ReplicatedVideoTime;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Replicated, Category = "Exhibit Network")
	FVector ReplicatedLocation;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Replicated, Category = "Exhibit Network")
	FRotator ReplicatedRotation;

	UFUNCTION(BlueprintCallable, Category = "Exhibit Interaction")
	void OnHoverStart(AVRPawn* Interactor);

	UFUNCTION(BlueprintCallable, Category = "Exhibit Interaction")
	void OnHoverEnd(AVRPawn* Interactor);

	UFUNCTION(BlueprintCallable, Category = "Exhibit Interaction")
	void OnSelect(AVRPawn* Interactor);

	UFUNCTION(BlueprintCallable, Category = "Exhibit Interaction")
	void OnDeselect(AVRPawn* Interactor);

	UFUNCTION(BlueprintCallable, Category = "Exhibit Interaction")
	void OnGrab(AVRPawn* Interactor);

	UFUNCTION(BlueprintCallable, Category = "Exhibit Interaction")
	void OnRelease(AVRPawn* Interactor);

	UFUNCTION(BlueprintCallable, Category = "Exhibit UI")
	void ShowInfo();

	UFUNCTION(BlueprintCallable, Category = "Exhibit UI")
	void HideInfo();

	UFUNCTION(BlueprintImplementableEvent, Category = "Exhibit Events")
	void OnExhibitHovered();

	UFUNCTION(BlueprintImplementableEvent, Category = "Exhibit Events")
	void OnExhibitUnhovered();

	UFUNCTION(BlueprintImplementableEvent, Category = "Exhibit Events")
	void OnExhibitSelected();

	UFUNCTION(BlueprintImplementableEvent, Category = "Exhibit Events")
	void OnExhibitDeselected();

	UFUNCTION(BlueprintCallable, Category = "Exhibit Media")
	void PlayVideo();

	UFUNCTION(BlueprintCallable, Category = "Exhibit Media")
	void PauseVideo();

	UFUNCTION(BlueprintCallable, Category = "Exhibit Media")
	void StopVideo();

	UFUNCTION(BlueprintCallable, Category = "Exhibit Media")
	void SyncAudioToVideo();

	UFUNCTION(BlueprintCallable, Category = "Exhibit Media")
	bool IsVideoPlaying() const;

protected:
	UFUNCTION()
	void OnComponentBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	UFUNCTION()
	void OnComponentEndOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp, int32 OtherBodyIndex);

	UFUNCTION()
	void OnMediaOpened(FString OpenedUrl);

	UFUNCTION()
	void OnMediaClosed();

	UFUNCTION()
	void OnRep_CurrentState();

	UFUNCTION()
	void OnRep_InfoVisible();

	UFUNCTION()
	void OnRep_VideoState();

	UFUNCTION(Server, Reliable, WithValidation)
	void Server_SetExhibitState(EExhibitState NewState, int32 PlayerId);
	void Server_SetExhibitState_Implementation(EExhibitState NewState, int32 PlayerId);
	bool Server_SetExhibitState_Validate(EExhibitState NewState, int32 PlayerId);

	UFUNCTION(Server, Reliable, WithValidation)
	void Server_PlayVideo(int32 PlayerId);
	void Server_PlayVideo_Implementation(int32 PlayerId);
	bool Server_PlayVideo_Validate(int32 PlayerId);

	UFUNCTION(Server, Reliable, WithValidation)
	void Server_PauseVideo(int32 PlayerId);
	void Server_PauseVideo_Implementation(int32 PlayerId);
	bool Server_PauseVideo_Validate(int32 PlayerId);

	UFUNCTION(Server, Reliable, WithValidation)
	void Server_StopVideo(int32 PlayerId);
	void Server_StopVideo_Implementation(int32 PlayerId);
	bool Server_StopVideo_Validate(int32 PlayerId);

	UFUNCTION(Server, Reliable, WithValidation)
	void Server_UpdateTransform(const FVector& Location, const FRotator& Rotation);
	void Server_UpdateTransform_Implementation(const FVector& Location, const FRotator& Rotation);
	bool Server_UpdateTransform_Validate(const FVector& Location, const FRotator& Rotation);

	UFUNCTION(NetMulticast, Reliable)
	void Multicast_OnExhibitStateChanged(EExhibitState NewState, int32 PlayerId);
	void Multicast_OnExhibitStateChanged_Implementation(EExhibitState NewState, int32 PlayerId);

	UFUNCTION(NetMulticast, Reliable)
	void Multicast_OnVideoStateChanged(bool bPlaying, float Time);
	void Multicast_OnVideoStateChanged_Implementation(bool bPlaying, float Time);

	FVector OriginalScale;
	FLinearColor OriginalColor;

	UPROPERTY()
	AVRPawn* CurrentInteractor;

	UPROPERTY()
	bool bIsVideoPlaying;

	UPROPERTY()
	float LastVideoTime;

	UPROPERTY()
	FTimerHandle SyncTimerHandle;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Exhibit Network")
	float NetworkSyncInterval;

	float LastNetworkSyncTime;

	void SyncExhibitStateToClients();
	void ApplyRemoteState();
};
