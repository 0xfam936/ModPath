import pyfiglet
from colorama import Fore
from .utils import clear_screen

def banner(title:str,subtitle:str):
        try:
            banner_text = pyfiglet.figlet_format(title, font="slant")
        except:
            banner_text = "TCP Server"

        clear_screen()

        print(f"{Fore.RED}{banner_text}")
        print(f"{Fore.RED}{'='*60}")
        print(subtitle)
        print(f"{Fore.RED}{'='*60}\n")
