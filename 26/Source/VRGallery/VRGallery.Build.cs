using UnrealBuildTool;

public class VRGallery : ModuleRules
{
	public VRGallery(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
	
		PublicDependencyModuleNames.AddRange(new string[] 
		{ 
			"Core", 
			"CoreUObject", 
			"Engine", 
			"InputCore",
			"HeadMountedDisplay",
			"EnhancedInput",
			"UMG",
			"Slate",
			"SlateCore",
			"Media",
			"MediaAssets",
			"MediaUtils",
			"NetCore",
			"OnlineSubsystem",
			"OnlineSubsystemUtils",
			"Sockets",
			"Networking"
		});

		PrivateDependencyModuleNames.AddRange(new string[] 
		{ 
			"NavigationSystem",
			"AIModule",
			"VivoxVoiceChat"
		});
	}
}
