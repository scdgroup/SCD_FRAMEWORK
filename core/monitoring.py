from core.my_enums import option_choice, others_choice,show_monitoring_menu




def monitoring_menu(rad_use):
    show_monitoring_menu(rad_use)
    while True:
        choice = option_choice("monitoring")

        if choice == "0" or choice == "back":
            return "back"
        elif choice == "1":

            return '1'
        elif choice == "2":
            return '2'
        elif choice == "3":
            return '3'
        elif choice == "4":
            return "exit"
        elif choice!='4' and choice!='3' and choice!='2' and choice!='1' and choice!='0' and choice!='back':
            others_choice(choice, "monitoring")
        else:
            print("Invalid choice. Please try again.")