using UnrealBuildTool;
using System.Collections.Generic;

public class VRGalleryTarget : TargetRules
{
	public VRGalleryTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V2;
		ExtraModuleNames.AddRange( new string[] { "VRGallery" } );
	}
}
