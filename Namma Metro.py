from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def launch_app_and_click(
        server_url="http://127.0.0.1:4723",
        device_name="emulator-5554",
        platform_version="16"
):
    """
    Launches Namma Metro app and clicks an element
    """

    # --- Appium options ---
    options = UiAutomator2Options()
    options.platformName = "Android"
    options.automationName = "UiAutomator2"
    options.udid = device_name
    options.platformVersion = platform_version

    # App details (exported activity)
    options.appPackage = "com.aum.nammametro"
    options.appActivity = "com.aum.nammametro.Activity.SplashScreen"
    # options.appActivity = "com.aum.nammametro.Activity.MainActivity"
    options.appWaitActivity = "*"

    # Stability settings
    options.noReset = False
    options.set_capability("forceAppLaunch",True)
    options.newCommandTimeout = 300
    options.uiautomator2ServerLaunchTimeout = 60000
    options.uiautomator2ServerInstallTimeout = 60000

    # --- Start driver ---
    driver = webdriver.Remote(server_url, options=options)
    driver.terminate_app("com.aum.nammametro")
    driver.activate_app("com.aum.nammametro")

    wait = WebDriverWait(driver, 30)

    
    # element = wait.until(
    #     EC.element_to_be_clickable(
    #         (AppiumBy.XPATH, "(//android.widget.ImageView[@resource-id='com.aum.nammametro:id/image_menu_icon'])[1]")
    #     )
    # )
    # element.click()

    qr = wait.until(
      EC.element_to_be_clickable(
         (AppiumBy.XPATH, "(//android.widget.ImageView[@resource-id='com.aum.nammametro:id/image_menu_icon'])[2]") 
        )
    )
    qr.click() 

    cm = wait.until(
        EC.element_to_be_clickable(
            (AppiumBy.XPATH, "//android.widget.LinearLayout[@content-desc='COMPLETED']")
        

)

    )
    cm.click()

    viewt = wait.until(
     EC.element_to_be_clickable(
      (AppiumBy.XPATH, "(//android.widget.ImageView[@content-desc='start'])[1]")
       )
   )

    viewt.click()

    Back = wait.until(
       EC.element_to_be_clickable(
           (AppiumBy.XPATH, "//android.widget.LinearLayout[@content-desc='OTHERS']")
       )  

    )
    Back.click()


    other = wait.until(
        EC.element_to_be_clickable(
        (AppiumBy.XPATH, "//android.widget.TextView[@text='OTHERS']")
        )
    )

    other.click()

    PF = wait.until(
         EC.element_to_be_clickable(
             (AppiumBy.XPATH, "//androidx.recyclerview.widget.RecyclerView[@resource-id='com.aum.nammametro:id/recyclerview_success_ticket_list']/android.widget.LinearLayout")
         )
    )
    PF.click()

    print("Clicked the element successfully")

    return driver


if __name__ == "__main__":
    driver = launch_app_and_click()
    input("Press Enter to close the app...")
    driver.quit()

