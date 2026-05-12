using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.Rendering;

[System.Serializable]
public class BuildingGroup
{
    public string groupName = "Group";
    public List<string> objFilePaths = new List<string>();
    public Material defaultMaterial;
    public Vector3 positionOffset = Vector3.zero;
    public Vector3 rotationOffset = Vector3.zero;
    public Vector3 scaleOffset = Vector3.one;
    public bool loadOnStart = false;
    public bool isLoaded = false;
    
    [System.NonSerialized]
    public GameObject groupObject;
}

[System.Serializable]
public class RoomInfo
{
    public string roomName = "Room";
    public Vector3 centerPosition = Vector3.zero;
    public Vector3 size = new Vector3(5.0f, 3.0f, 5.0f);
    public bool showUI = true;
    
    public bool IsPointInside(Vector3 point)
    {
        Vector3 min = centerPosition - size * 0.5f;
        Vector3 max = centerPosition + size * 0.5f;
        
        return point.x >= min.x && point.x <= max.x &&
               point.y >= min.y && point.y <= max.y &&
               point.z >= min.z && point.z <= max.z;
    }
}

public class BuildingLoader : MonoBehaviour
{
    [Header("Building Settings")]
    public string objFilePath;
    public Material defaultMaterial;
    public Vector3 positionOffset = Vector3.zero;
    public Vector3 rotationOffset = Vector3.zero;
    public Vector3 scaleOffset = Vector3.one;
    
    [Header("Group Loading")]
    public List<BuildingGroup> buildingGroups = new List<BuildingGroup>();
    public string currentGroupName = "";
    
    [Header("Room Detection")]
    public List<RoomInfo> rooms = new List<RoomInfo>();
    public Transform playerTransform;
    public string currentRoomName = "";
    public bool autoDetectRooms = true;
    
    [Header("Large Mesh Support")]
    public bool use32BitIndices = true;
    public int maxVerticesPerSubmesh = 65000;
    public bool splitLargeMeshes = false;
    
    [Header("Auto Load")]
    public bool autoLoadOnStart = false;
    
    private GameObject loadedBuilding;
    private const int MAX_16BIT_VERTICES = 65535;
    
    public delegate void OnRoomChanged(string newRoomName);
    public event OnRoomChanged RoomChanged;
    
    public delegate void OnGroupLoaded(string groupName);
    public event OnGroupLoaded GroupLoaded;
    
    void Start()
    {
        if (autoLoadOnStart && !string.IsNullOrEmpty(objFilePath))
        {
            LoadBuilding(objFilePath);
        }
        
        LoadAutoStartGroups();
        
        if (playerTransform == null)
        {
            Camera mainCamera = Camera.main;
            if (mainCamera != null)
            {
                playerTransform = mainCamera.transform;
            }
        }
    }
    
    void Update()
    {
        if (autoDetectRooms && playerTransform != null)
        {
            DetectCurrentRoom();
        }
    }
    
    void LoadAutoStartGroups()
    {
        foreach (BuildingGroup group in buildingGroups)
        {
            if (group.loadOnStart && !group.isLoaded)
            {
                LoadGroup(group);
            }
        }
    }
    
    void DetectCurrentRoom()
    {
        if (playerTransform == null)
            return;
        
        string newRoomName = "";
        
        foreach (RoomInfo room in rooms)
        {
            if (room.IsPointInside(playerTransform.position))
            {
                newRoomName = room.roomName;
                break;
            }
        }
        
        if (newRoomName != currentRoomName)
        {
            currentRoomName = newRoomName;
            RoomChanged?.Invoke(currentRoomName);
        }
    }
    
    public void LoadBuilding(string filePath)
    {
        if (string.IsNullOrEmpty(filePath))
        {
            Debug.LogError("OBJ file path is empty.");
            return;
        }
        
        if (!File.Exists(filePath))
        {
            Debug.LogError("OBJ file not found: " + filePath);
            return;
        }
        
        UnloadBuilding();
        
        try
        {
            List<Mesh> meshes = ParseOBJ(filePath);
            if (meshes == null || meshes.Count == 0)
            {
                Debug.LogError("Failed to parse OBJ file: " + filePath);
                return;
            }
            
            loadedBuilding = new GameObject("LoadedBuilding_" + Path.GetFileNameWithoutExtension(filePath));
            loadedBuilding.transform.SetParent(transform);
            loadedBuilding.transform.localPosition = positionOffset;
            loadedBuilding.transform.localEulerAngles = rotationOffset;
            loadedBuilding.transform.localScale = scaleOffset;
            
            for (int i = 0; i < meshes.Count; i++)
            {
                Mesh mesh = meshes[i];
                string subObjectName = meshes.Count > 1 ? $"SubMesh_{i}" : "Mesh";
                
                GameObject subObject = new GameObject(subObjectName);
                subObject.transform.SetParent(loadedBuilding.transform, false);
                
                MeshFilter meshFilter = subObject.AddComponent<MeshFilter>();
                meshFilter.mesh = mesh;
                
                MeshRenderer meshRenderer = subObject.AddComponent<MeshRenderer>();
                meshRenderer.material = defaultMaterial != null ? defaultMaterial : new Material(Shader.Find("Standard"));
                
                if (mesh.vertexCount <= MAX_16BIT_VERTICES)
                {
                    MeshCollider collider = subObject.AddComponent<MeshCollider>();
                    collider.sharedMesh = mesh;
                }
                else
                {
                    Debug.LogWarning($"Mesh {subObjectName} has {mesh.vertexCount} vertices, skipping MeshCollider (limit: {MAX_16BIT_VERTICES})");
                }
            }
            
            Debug.Log($"Successfully loaded building with {meshes.Count} mesh(es): {filePath}");
        }
        catch (System.Exception ex)
        {
            Debug.LogError("Error loading OBJ file: " + ex.Message + "\n" + ex.StackTrace);
        }
    }
    
    public void UnloadBuilding()
    {
        if (loadedBuilding != null)
        {
            Destroy(loadedBuilding);
            loadedBuilding = null;
        }
    }
    
    public void LoadGroup(int groupIndex)
    {
        if (groupIndex < 0 || groupIndex >= buildingGroups.Count)
        {
            Debug.LogError("Group index out of range: " + groupIndex);
            return;
        }
        
        LoadGroup(buildingGroups[groupIndex]);
    }
    
    public void LoadGroup(string groupName)
    {
        BuildingGroup group = buildingGroups.Find(g => g.groupName == groupName);
        if (group != null)
        {
            LoadGroup(group);
        }
        else
        {
            Debug.LogError("Group not found: " + groupName);
        }
    }
    
    void LoadGroup(BuildingGroup group)
    {
        if (group == null || group.isLoaded)
            return;
        
        if (group.objFilePaths == null || group.objFilePaths.Count == 0)
        {
            Debug.LogWarning("Group has no OBJ files: " + group.groupName);
            return;
        }
        
        group.groupObject = new GameObject("Group_" + group.groupName);
        group.groupObject.transform.SetParent(transform);
        group.groupObject.transform.localPosition = group.positionOffset;
        group.groupObject.transform.localEulerAngles = group.rotationOffset;
        group.groupObject.transform.localScale = group.scaleOffset;
        
        foreach (string filePath in group.objFilePaths)
        {
            if (string.IsNullOrEmpty(filePath) || !File.Exists(filePath))
            {
                Debug.LogWarning("Skipping invalid file: " + filePath);
                continue;
            }
            
            try
            {
                List<Mesh> meshes = ParseOBJ(filePath);
                if (meshes == null || meshes.Count == 0)
                {
                    Debug.LogWarning("Failed to parse: " + filePath);
                    continue;
                }
                
                for (int i = 0; i < meshes.Count; i++)
                {
                    Mesh mesh = meshes[i];
                    string subObjectName = meshes.Count > 1 ? 
                        $"{Path.GetFileNameWithoutExtension(filePath)}_{i}" : 
                        Path.GetFileNameWithoutExtension(filePath);
                    
                    GameObject subObject = new GameObject(subObjectName);
                    subObject.transform.SetParent(group.groupObject.transform, false);
                    
                    MeshFilter meshFilter = subObject.AddComponent<MeshFilter>();
                    meshFilter.mesh = mesh;
                    
                    MeshRenderer meshRenderer = subObject.AddComponent<MeshRenderer>();
                    meshRenderer.material = group.defaultMaterial != null ? 
                        group.defaultMaterial : 
                        (defaultMaterial != null ? defaultMaterial : new Material(Shader.Find("Standard")));
                    
                    if (mesh.vertexCount <= MAX_16BIT_VERTICES)
                    {
                        MeshCollider collider = subObject.AddComponent<MeshCollider>();
                        collider.sharedMesh = mesh;
                    }
                }
            }
            catch (System.Exception ex)
            {
                Debug.LogError("Error loading: " + filePath + " - " + ex.Message);
            }
        }
        
        group.isLoaded = true;
        currentGroupName = group.groupName;
        GroupLoaded?.Invoke(group.groupName);
        Debug.Log("Successfully loaded group: " + group.groupName);
    }
    
    public void UnloadGroup(int groupIndex)
    {
        if (groupIndex < 0 || groupIndex >= buildingGroups.Count)
        {
            Debug.LogError("Group index out of range: " + groupIndex);
            return;
        }
        
        UnloadGroup(buildingGroups[groupIndex]);
    }
    
    public void UnloadGroup(string groupName)
    {
        BuildingGroup group = buildingGroups.Find(g => g.groupName == groupName);
        if (group != null)
        {
            UnloadGroup(group);
        }
    }
    
    void UnloadGroup(BuildingGroup group)
    {
        if (group == null || !group.isLoaded)
            return;
        
        if (group.groupObject != null)
        {
            Destroy(group.groupObject);
            group.groupObject = null;
        }
        
        group.isLoaded = false;
        if (currentGroupName == group.groupName)
        {
            currentGroupName = "";
        }
        Debug.Log("Unloaded group: " + group.groupName);
    }
    
    public void ToggleGroup(int groupIndex)
    {
        if (groupIndex < 0 || groupIndex >= buildingGroups.Count)
            return;
        
        BuildingGroup group = buildingGroups[groupIndex];
        if (group.isLoaded)
        {
            UnloadGroup(group);
        }
        else
        {
            LoadGroup(group);
        }
    }
    
    public void ToggleGroup(string groupName)
    {
        BuildingGroup group = buildingGroups.Find(g => g.groupName == groupName);
        if (group != null)
        {
            if (group.isLoaded)
            {
                UnloadGroup(group);
            }
            else
            {
                LoadGroup(group);
            }
        }
    }
    
    public void UnloadAllGroups()
    {
        foreach (BuildingGroup group in buildingGroups)
        {
            UnloadGroup(group);
        }
        currentGroupName = "";
    }
    
    public List<string> GetAllGroupNames()
    {
        List<string> names = new List<string>();
        foreach (BuildingGroup group in buildingGroups)
        {
            names.Add(group.groupName);
        }
        return names;
    }
    
    public List<string> GetLoadedGroupNames()
    {
        List<string> names = new List<string>();
        foreach (BuildingGroup group in buildingGroups)
        {
            if (group.isLoaded)
            {
                names.Add(group.groupName);
            }
        }
        return names;
    }
    
    public string GetCurrentRoomName()
    {
        return currentRoomName;
    }
    
    public List<string> GetAllRoomNames()
    {
        List<string> names = new List<string>();
        foreach (RoomInfo room in rooms)
        {
            names.Add(room.roomName);
        }
        return names;
    }
    
    public GameObject GetLoadedBuilding()
    {
        return loadedBuilding;
    }
    
    public bool IsBuildingLoaded()
    {
        return loadedBuilding != null;
    }
    
    public bool IsGroupLoaded(string groupName)
    {
        BuildingGroup group = buildingGroups.Find(g => g.groupName == groupName);
        return group != null && group.isLoaded;
    }
    
    private List<Mesh> ParseOBJ(string filePath)
    {
        List<Vector3> vertices = new List<Vector3>();
        List<Vector3> normals = new List<Vector3>();
        List<Vector2> uvs = new List<Vector2>();
        List<Face> faces = new List<Face>();
        
        string[] lines = File.ReadAllLines(filePath);
        Debug.Log($"Parsing OBJ file: {lines.Length} lines");
        
        foreach (string line in lines)
        {
            if (string.IsNullOrWhiteSpace(line))
                continue;
            
            string[] parts = line.Split(new char[] { ' ' }, System.StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length == 0)
                continue;
            
            switch (parts[0])
            {
                case "v":
                    if (parts.Length >= 4)
                    {
                        float x = SafeParseFloat(parts[1]);
                        float y = SafeParseFloat(parts[2]);
                        float z = SafeParseFloat(parts[3]);
                        vertices.Add(new Vector3(x, y, z));
                    }
                    break;
                    
                case "vn":
                    if (parts.Length >= 4)
                    {
                        float x = SafeParseFloat(parts[1]);
                        float y = SafeParseFloat(parts[2]);
                        float z = SafeParseFloat(parts[3]);
                        normals.Add(new Vector3(x, y, z));
                    }
                    break;
                    
                case "vt":
                    if (parts.Length >= 3)
                    {
                        float x = SafeParseFloat(parts[1]);
                        float y = SafeParseFloat(parts[2]);
                        uvs.Add(new Vector2(x, y));
                    }
                    break;
                    
                case "f":
                    ParseFaceLine(parts, faces);
                    break;
            }
        }
        
        Debug.Log($"Parsed: {vertices.Count} vertices, {normals.Count} normals, {uvs.Count} uvs, {faces.Count} faces");
        
        if (vertices.Count == 0 || faces.Count == 0)
        {
            return null;
        }
        
        return BuildMeshes(vertices, normals, uvs, faces, Path.GetFileNameWithoutExtension(filePath));
    }
    
    private void ParseFaceLine(string[] parts, List<Face> faces)
    {
        List<FaceVertex> faceVertices = new List<FaceVertex>();
        
        for (int i = 1; i < parts.Length; i++)
        {
            string[] faceParts = parts[i].Split('/');
            FaceVertex fv = new FaceVertex();
            
            if (faceParts.Length >= 1 && !string.IsNullOrEmpty(faceParts[0]))
            {
                fv.vertexIndex = int.Parse(faceParts[0]) - 1;
            }
            
            if (faceParts.Length >= 2 && !string.IsNullOrEmpty(faceParts[1]))
            {
                fv.uvIndex = int.Parse(faceParts[1]) - 1;
                fv.hasUV = true;
            }
            
            if (faceParts.Length >= 3 && !string.IsNullOrEmpty(faceParts[2]))
            {
                fv.normalIndex = int.Parse(faceParts[2]) - 1;
                fv.hasNormal = true;
            }
            
            faceVertices.Add(fv);
        }
        
        if (faceVertices.Count >= 3)
        {
            for (int i = 1; i < faceVertices.Count - 1; i++)
            {
                Face face = new Face();
                face.v0 = faceVertices[0];
                face.v1 = faceVertices[i];
                face.v2 = faceVertices[i + 1];
                faces.Add(face);
            }
        }
    }
    
    private List<Mesh> BuildMeshes(List<Vector3> vertices, List<Vector3> normals, List<Vector2> uvs, List<Face> faces, string meshName)
    {
        List<Mesh> meshes = new List<Mesh>();
        
        if (splitLargeMeshes && vertices.Count > maxVerticesPerSubmesh)
        {
            Debug.Log($"Splitting large mesh ({vertices.Count} vertices) into submeshes of {maxVerticesPerSubmesh}");
            meshes = SplitMeshIntoSubmeshes(vertices, normals, uvs, faces, meshName);
        }
        else
        {
            Mesh mesh = BuildSingleMesh(vertices, normals, uvs, faces, meshName);
            if (mesh != null)
            {
                meshes.Add(mesh);
            }
        }
        
        return meshes;
    }
    
    private Mesh BuildSingleMesh(List<Vector3> vertices, List<Vector3> normals, List<Vector2> uvs, List<Face> faces, string meshName)
    {
        Dictionary<FaceVertex, int> vertexMap = new Dictionary<FaceVertex, int>();
        List<Vector3> meshVertices = new List<Vector3>();
        List<Vector3> meshNormals = new List<Vector3>();
        List<Vector2> meshUVs = new List<Vector2>();
        List<int> meshTriangles = new List<int>();
        
        foreach (Face face in faces)
        {
            int i0 = GetOrCreateVertex(face.v0, vertices, normals, uvs, vertexMap, meshVertices, meshNormals, meshUVs);
            int i1 = GetOrCreateVertex(face.v1, vertices, normals, uvs, vertexMap, meshVertices, meshNormals, meshUVs);
            int i2 = GetOrCreateVertex(face.v2, vertices, normals, uvs, vertexMap, meshVertices, meshNormals, meshUVs);
            
            meshTriangles.Add(i0);
            meshTriangles.Add(i1);
            meshTriangles.Add(i2);
        }
        
        if (meshVertices.Count == 0 || meshTriangles.Count == 0)
        {
            return null;
        }
        
        Mesh mesh = new Mesh();
        mesh.name = meshName;
        
        if (use32BitIndices && meshVertices.Count > MAX_16BIT_VERTICES)
        {
            mesh.indexFormat = IndexFormat.UInt32;
            Debug.Log($"Using 32-bit indices for mesh with {meshVertices.Count} vertices");
        }
        
        mesh.vertices = meshVertices.ToArray();
        mesh.triangles = meshTriangles.ToArray();
        
        if (meshNormals.Count == meshVertices.Count)
        {
            mesh.normals = meshNormals.ToArray();
        }
        else
        {
            mesh.RecalculateNormals();
        }
        
        if (meshUVs.Count == meshVertices.Count)
        {
            mesh.uv = meshUVs.ToArray();
        }
        
        mesh.RecalculateBounds();
        mesh.RecalculateTangents();
        
        return mesh;
    }
    
    private List<Mesh> SplitMeshIntoSubmeshes(List<Vector3> vertices, List<Vector3> normals, List<Vector2> uvs, List<Face> faces, string baseName)
    {
        List<Mesh> meshes = new List<Mesh>();
        Dictionary<int, List<Face>> vertexFaceMap = new Dictionary<int, List<Face>>();
        
        for (int i = 0; i < faces.Count; i++)
        {
            Face face = faces[i];
            AddFaceToMap(face.v0.vertexIndex, face, vertexFaceMap);
            AddFaceToMap(face.v1.vertexIndex, face, vertexFaceMap);
            AddFaceToMap(face.v2.vertexIndex, face, vertexFaceMap);
        }
        
        HashSet<Face> processedFaces = new HashSet<Face>();
        int submeshIndex = 0;
        
        foreach (Face face in faces)
        {
            if (processedFaces.Contains(face))
                continue;
            
            List<Face> submeshFaces = new List<Face>();
            HashSet<int> submeshVertices = new HashSet<int>();
            Queue<Face> faceQueue = new Queue<Face>();
            faceQueue.Enqueue(face);
            
            while (faceQueue.Count > 0 && submeshVertices.Count < maxVerticesPerSubmesh)
            {
                Face currentFace = faceQueue.Dequeue();
                
                if (processedFaces.Contains(currentFace))
                    continue;
                
                int v0 = currentFace.v0.vertexIndex;
                int v1 = currentFace.v1.vertexIndex;
                int v2 = currentFace.v2.vertexIndex;
                
                if (submeshVertices.Count >= maxVerticesPerSubmesh - 3)
                    continue;
                
                submeshFaces.Add(currentFace);
                processedFaces.Add(currentFace);
                submeshVertices.Add(v0);
                submeshVertices.Add(v1);
                submeshVertices.Add(v2);
                
                EnqueueConnectedFaces(v0, vertexFaceMap, processedFaces, faceQueue);
                EnqueueConnectedFaces(v1, vertexFaceMap, processedFaces, faceQueue);
                EnqueueConnectedFaces(v2, vertexFaceMap, processedFaces, faceQueue);
            }
            
            if (submeshFaces.Count > 0)
            {
                Mesh submesh = BuildSingleMesh(vertices, normals, uvs, submeshFaces, $"{baseName}_Part{submeshIndex}");
                if (submesh != null)
                {
                    meshes.Add(submesh);
                    submeshIndex++;
                }
            }
        }
        
        return meshes;
    }
    
    private void AddFaceToMap(int vertexIndex, Face face, Dictionary<int, List<Face>> map)
    {
        if (!map.ContainsKey(vertexIndex))
        {
            map[vertexIndex] = new List<Face>();
        }
        map[vertexIndex].Add(face);
    }
    
    private void EnqueueConnectedFaces(int vertexIndex, Dictionary<int, List<Face>> map, HashSet<Face> processed, Queue<Face> queue)
    {
        if (map.ContainsKey(vertexIndex))
        {
            foreach (Face connectedFace in map[vertexIndex])
            {
                if (!processed.Contains(connectedFace))
                {
                    queue.Enqueue(connectedFace);
                }
            }
        }
    }
    
    private int GetOrCreateVertex(FaceVertex fv, List<Vector3> vertices, List<Vector3> normals, List<Vector2> uvs, 
        Dictionary<FaceVertex, int> vertexMap, List<Vector3> meshVertices, List<Vector3> meshNormals, List<Vector2> meshUVs)
    {
        if (vertexMap.ContainsKey(fv))
        {
            return vertexMap[fv];
        }
        
        int index = meshVertices.Count;
        meshVertices.Add(vertices[fv.vertexIndex]);
        
        if (fv.hasNormal && fv.normalIndex >= 0 && fv.normalIndex < normals.Count)
        {
            meshNormals.Add(normals[fv.normalIndex]);
        }
        
        if (fv.hasUV && fv.uvIndex >= 0 && fv.uvIndex < uvs.Count)
        {
            meshUVs.Add(uvs[fv.uvIndex]);
        }
        
        vertexMap[fv] = index;
        return index;
    }
    
    private float SafeParseFloat(string value)
    {
        if (float.TryParse(value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float result))
        {
            return result;
        }
        return 0f;
    }
    
    private struct FaceVertex
    {
        public int vertexIndex;
        public int normalIndex;
        public int uvIndex;
        public bool hasNormal;
        public bool hasUV;
        
        public override bool Equals(object obj)
        {
            if (!(obj is FaceVertex))
                return false;
            
            FaceVertex other = (FaceVertex)obj;
            return vertexIndex == other.vertexIndex && 
                   normalIndex == other.normalIndex && 
                   uvIndex == other.uvIndex &&
                   hasNormal == other.hasNormal &&
                   hasUV == other.hasUV;
        }
        
        public override int GetHashCode()
        {
            int hash = vertexIndex.GetHashCode();
            hash = (hash * 397) ^ normalIndex.GetHashCode();
            hash = (hash * 397) ^ uvIndex.GetHashCode();
            hash = (hash * 397) ^ hasNormal.GetHashCode();
            hash = (hash * 397) ^ hasUV.GetHashCode();
            return hash;
        }
    }
    
    private class Face
    {
        public FaceVertex v0;
        public FaceVertex v1;
        public FaceVertex v2;
    }
}
