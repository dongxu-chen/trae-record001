using UnityEngine;
using UnityEngine.UI;
using System.Collections.Generic;

public class UIManager : MonoBehaviour
{
    [Header("References")]
    public BuildingLoader buildingLoader;
    public MaterialSwitcher materialSwitcher;
    public CameraController cameraController;
    
    [Header("UI Panels")]
    public GameObject mainMenuPanel;
    public GameObject pauseMenuPanel;
    public GameObject loadingPanel;
    public GameObject groupPanel;
    
    [Header("UI Elements")]
    public Text currentMaterialText;
    public Text statusText;
    public InputField objFilePathInput;
    public Button loadButton;
    public Button nextMaterialButton;
    public Button previousMaterialButton;
    public Button resetMaterialButton;
    
    [Header("Room UI")]
    public Text currentRoomText;
    public Text cameraModeText;
    public string roomDisplayFormat = "当前位置: {0}";
    public string outdoorText = "室外";
    public string indoorText = "室内";
    public string unknownRoomText = "未定义区域";
    
    [Header("Group UI")]
    public Transform groupButtonContainer;
    public GameObject groupButtonPrefab;
    public Button groupPanelToggleButton;
    
    [Header("Settings")]
    public KeyCode menuKey = KeyCode.Escape;
    public KeyCode nextMaterialKey = KeyCode.RightBracket;
    public KeyCode previousMaterialKey = KeyCode.LeftBracket;
    public KeyCode groupPanelKey = KeyCode.G;
    
    private bool isPaused = false;
    private bool isMenuOpen = false;
    private bool isGroupPanelOpen = false;
    private Dictionary<string, Button> groupButtons = new Dictionary<string, Button>();
    
    void Start()
    {
        InitializeUI();
        InitializeGroupButtons();
        SubscribeToEvents();
        UpdateMaterialDisplay();
        UpdateCameraModeDisplay();
        UpdateRoomDisplay();
    }
    
    void Update()
    {
        HandleMenuToggle();
        HandleGroupPanelToggle();
        HandleKeyboardShortcuts();
    }
    
    void OnDestroy()
    {
        UnsubscribeFromEvents();
    }
    
    void InitializeUI()
    {
        if (mainMenuPanel != null)
        {
            mainMenuPanel.SetActive(true);
            isMenuOpen = true;
            SetCursorVisible(true);
        }
        
        if (pauseMenuPanel != null)
        {
            pauseMenuPanel.SetActive(false);
        }
        
        if (loadingPanel != null)
        {
            loadingPanel.SetActive(false);
        }
        
        if (groupPanel != null)
        {
            groupPanel.SetActive(false);
        }
        
        if (loadButton != null)
        {
            loadButton.onClick.AddListener(OnLoadButtonClicked);
        }
        
        if (nextMaterialButton != null)
        {
            nextMaterialButton.onClick.AddListener(OnNextMaterialClicked);
        }
        
        if (previousMaterialButton != null)
        {
            previousMaterialButton.onClick.AddListener(OnPreviousMaterialClicked);
        }
        
        if (resetMaterialButton != null)
        {
            resetMaterialButton.onClick.AddListener(OnResetMaterialClicked);
        }
        
        if (groupPanelToggleButton != null)
        {
            groupPanelToggleButton.onClick.AddListener(OnToggleGroupPanel);
        }
    }
    
    void InitializeGroupButtons()
    {
        if (buildingLoader == null || groupButtonContainer == null || groupButtonPrefab == null)
            return;
        
        List<string> groupNames = buildingLoader.GetAllGroupNames();
        
        foreach (string groupName in groupNames)
        {
            if (groupButtons.ContainsKey(groupName))
                continue;
            
            GameObject buttonObj = Instantiate(groupButtonPrefab, groupButtonContainer);
            Button button = buttonObj.GetComponent<Button>();
            
            if (button != null)
            {
                Text buttonText = button.GetComponentInChildren<Text>();
                if (buttonText != null)
                {
                    buttonText.text = groupName;
                }
                
                string capturedName = groupName;
                button.onClick.AddListener(() => OnGroupButtonClicked(capturedName));
                
                groupButtons[groupName] = button;
                UpdateGroupButtonState(groupName);
            }
        }
    }
    
    void SubscribeToEvents()
    {
        if (buildingLoader != null)
        {
            buildingLoader.RoomChanged += OnRoomChanged;
            buildingLoader.GroupLoaded += OnGroupLoaded;
        }
    }
    
    void UnsubscribeFromEvents()
    {
        if (buildingLoader != null)
        {
            buildingLoader.RoomChanged -= OnRoomChanged;
            buildingLoader.GroupLoaded -= OnGroupLoaded;
        }
    }
    
    void HandleMenuToggle()
    {
        if (Input.GetKeyDown(menuKey))
        {
            if (isMenuOpen)
            {
                CloseMenu();
            }
            else
            {
                OpenPauseMenu();
            }
        }
    }
    
    void HandleGroupPanelToggle()
    {
        if (Input.GetKeyDown(groupPanelKey))
        {
            OnToggleGroupPanel();
        }
    }
    
    void HandleKeyboardShortcuts()
    {
        if (isMenuOpen)
            return;
        
        if (Input.GetKeyDown(nextMaterialKey))
        {
            OnNextMaterialClicked();
        }
        else if (Input.GetKeyDown(previousMaterialKey))
        {
            OnPreviousMaterialClicked();
        }
    }
    
    public void OpenPauseMenu()
    {
        if (pauseMenuPanel != null)
        {
            pauseMenuPanel.SetActive(true);
            isMenuOpen = true;
            isPaused = true;
            Time.timeScale = 0f;
            SetCursorVisible(true);
        }
    }
    
    public void CloseMenu()
    {
        if (mainMenuPanel != null)
        {
            mainMenuPanel.SetActive(false);
        }
        
        if (pauseMenuPanel != null)
        {
            pauseMenuPanel.SetActive(false);
        }
        
        if (groupPanel != null)
        {
            groupPanel.SetActive(false);
            isGroupPanelOpen = false;
        }
        
        isMenuOpen = false;
        isPaused = false;
        Time.timeScale = 1f;
        SetCursorVisible(false);
    }
    
    public void OnToggleGroupPanel()
    {
        if (groupPanel == null)
            return;
        
        isGroupPanelOpen = !isGroupPanelOpen;
        groupPanel.SetActive(isGroupPanelOpen);
        
        if (isGroupPanelOpen)
        {
            SetCursorVisible(true);
        }
        else if (!isMenuOpen)
        {
            SetCursorVisible(false);
        }
    }
    
    void SetCursorVisible(bool visible)
    {
        Cursor.visible = visible;
        Cursor.lockState = visible ? CursorLockMode.None : CursorLockMode.Locked;
    }
    
    public void OnStartButtonClicked()
    {
        CloseMenu();
    }
    
    public void OnLoadButtonClicked()
    {
        if (buildingLoader == null)
        {
            UpdateStatus("BuildingLoader not found!");
            return;
        }
        
        string filePath = objFilePathInput != null ? objFilePathInput.text : "";
        
        if (string.IsNullOrEmpty(filePath))
        {
            UpdateStatus("Please enter OBJ file path");
            return;
        }
        
        ShowLoadingPanel(true);
        UpdateStatus("Loading building...");
        
        StartCoroutine(LoadBuildingCoroutine(filePath));
    }
    
    System.Collections.IEnumerator LoadBuildingCoroutine(string filePath)
    {
        yield return null;
        
        buildingLoader.LoadBuilding(filePath);
        
        bool loaded = buildingLoader.IsBuildingLoaded();
        UpdateStatus(loaded ? "Building loaded successfully!" : "Failed to load building");
        
        ShowLoadingPanel(false);
        
        if (loaded)
        {
            CloseMenu();
        }
    }
    
    public void OnGroupButtonClicked(string groupName)
    {
        if (buildingLoader == null)
            return;
        
        buildingLoader.ToggleGroup(groupName);
        UpdateGroupButtonState(groupName);
        
        string status = buildingLoader.IsGroupLoaded(groupName) ? 
            $"Loaded group: {groupName}" : 
            $"Unloaded group: {groupName}";
        UpdateStatus(status);
    }
    
    public void OnNextMaterialClicked()
    {
        if (materialSwitcher == null)
        {
            UpdateStatus("MaterialSwitcher not found!");
            return;
        }
        
        materialSwitcher.SwitchToNextMaterial();
        UpdateMaterialDisplay();
    }
    
    public void OnPreviousMaterialClicked()
    {
        if (materialSwitcher == null)
        {
            UpdateStatus("MaterialSwitcher not found!");
            return;
        }
        
        materialSwitcher.SwitchToPreviousMaterial();
        UpdateMaterialDisplay();
    }
    
    public void OnResetMaterialClicked()
    {
        if (materialSwitcher == null)
        {
            UpdateStatus("MaterialSwitcher not found!");
            return;
        }
        
        materialSwitcher.ResetToOriginalMaterial();
        UpdateMaterialDisplay();
    }
    
    void OnRoomChanged(string newRoomName)
    {
        UpdateRoomDisplay();
    }
    
    void OnGroupLoaded(string groupName)
    {
        UpdateGroupButtonState(groupName);
    }
    
    void UpdateMaterialDisplay()
    {
        if (currentMaterialText != null && materialSwitcher != null)
        {
            string materialName = materialSwitcher.GetCurrentMaterialName();
            int total = materialSwitcher.GetMaterialCount();
            currentMaterialText.text = string.Format("Material: {0} ({1}/{2})", 
                materialName, 
                materialSwitcher.currentMaterialIndex + 1, 
                total);
        }
    }
    
    void UpdateCameraModeDisplay()
    {
        if (cameraModeText != null && cameraController != null)
        {
            CameraMode mode = cameraController.GetCurrentMode();
            string modeText = mode == CameraMode.Outdoor ? outdoorText : indoorText;
            cameraModeText.text = string.Format("模式: {0}", modeText);
        }
    }
    
    void UpdateRoomDisplay()
    {
        if (currentRoomText == null)
            return;
        
        string roomName = buildingLoader != null ? buildingLoader.GetCurrentRoomName() : "";
        
        if (string.IsNullOrEmpty(roomName))
        {
            if (cameraController != null)
            {
                CameraMode mode = cameraController.GetCurrentMode();
                roomName = mode == CameraMode.Outdoor ? outdoorText : unknownRoomText;
            }
            else
            {
                roomName = unknownRoomText;
            }
        }
        
        currentRoomText.text = string.Format(roomDisplayFormat, roomName);
    }
    
    void UpdateGroupButtonState(string groupName)
    {
        if (buildingLoader == null || !groupButtons.ContainsKey(groupName))
            return;
        
        Button button = groupButtons[groupName];
        if (button == null)
            return;
        
        bool isLoaded = buildingLoader.IsGroupLoaded(groupName);
        
        ColorBlock colors = button.colors;
        colors.normalColor = isLoaded ? Color.green : Color.white;
        button.colors = colors;
        
        Text buttonText = button.GetComponentInChildren<Text>();
        if (buttonText != null)
        {
            buttonText.text = isLoaded ? $"✓ {groupName}" : groupName;
        }
    }
    
    void UpdateStatus(string message)
    {
        if (statusText != null)
        {
            statusText.text = message;
        }
        Debug.Log("UIManager: " + message);
    }
    
    void ShowLoadingPanel(bool show)
    {
        if (loadingPanel != null)
        {
            loadingPanel.SetActive(show);
        }
    }
    
    public void OnResumeButtonClicked()
    {
        CloseMenu();
    }
    
    public void OnRestartButtonClicked()
    {
        UnityEngine.SceneManagement.SceneManager.LoadScene(
            UnityEngine.SceneManagement.SceneManager.GetActiveScene().buildIndex);
    }
    
    public void OnQuitButtonClicked()
    {
#if UNITY_EDITOR
        UnityEditor.EditorApplication.isPlaying = false;
#else
        Application.Quit();
#endif
    }
}
