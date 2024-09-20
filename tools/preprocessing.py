from tools.utils import days_between_dates, get_holidays, convert_floats_to_ints, transform_itemization_details, extract_vacation_dates

def preprocess(data, user_data, vacation, combine_categories=True):
    """
    Preprocesses the input data for billing cycles.

    This function takes the raw data, user data, and vacation details, and performs several preprocessing steps including calculating the number of days in each cycle, identifying holidays and vacations, transforming itemization details, and restructuring the data. 
    It ensures that the data is cleaned and organized for further usage.

    Args:
        data (dict): The raw data containing usage chart data list.
        user_data (dict): The user data including city, state, country, and zip code.
        vacation (list): The list of vacation dates.
        combine_categories (bool, optional): Whether to combine specific categories into 'otherGeneralUsage'. Defaults to True.

    Returns:
        dict: The preprocessed data with usage chart data list and user location.
        
    Raises:
        KeyError: If a required key is missing in the input data.
        TypeError: If there is a type mismatch in the input data.
    """
    try:
        usage_chart_data_list = data["payload"]["usageChartDataList"]
        # Get user metadata
        city = user_data['city']
        state = user_data['state']
        country = user_data['country']
        zipcode = user_data['zip']
        
        # Get vacation data for users
        # vacation = fetch_vacationdata(uuid)
        vacation_data = extract_vacation_dates (vacation)

        # Get US holidays for 2018 and 2025
        holidays_2016_2025 = get_holidays(country, state, 2016, 2025, True, True, vacation_data)
        
        categories = ["airConditioning", "alwaysOn", "cooking", "electricVehicle", "entertainment", "laundry", 
                      "lighting", "other", "pool", "refrigeration", "spaceHeating", "waterHeating"]
        
        for item in usage_chart_data_list:
            # Calculate the number of days between intervalStartDateFormatted and intervalEndDateFormatted
            start_date = item.get("intervalStartDateFormatted")
            end_date = item.get("intervalEndDateFormatted")
            if start_date and end_date:
                num_days = days_between_dates(start_date, end_date)
                item["num_days"] = num_days

            # Including the holidays within the interval range
            item["num_holidays"] = sum(1 for holiday in holidays_2016_2025
                                       if start_date <= holiday["date"] <= end_date)

            item["holidays"] = [holiday["name"] for holiday in holidays_2016_2025
                                if start_date <= holiday["date"] <= end_date]
            
            # Including vacation dates within the interval range
            #item["vacation"] = [vacation_date for vacation_date in vacation_data
            #                          if start_date <= vacation_date <= end_date]
            item["num_vacation"] = sum (1 for vacation_date in vacation_data if start_date <= vacation_date <= end_date)

            # Delete keys from each item
            keys_to_remove = ["intervalStart", "intervalEnd", "intervalStartDate", "intervalEndDate", "isWeekend", 
                               "isOngoingInterval", "isMissingDataInterval", 
                              "isTimestampPresent", "isBoundaryInterval", "peakDemand", "peakDemandCharges", "solarUser", 
                              "seasonalBillCycle", "estimatedConsumption", "solarGeneration", "userType", "miscCharges", "energyCharges", "fixedChargeApplicable"]
            
            for key in keys_to_remove:
                item.pop(key, None)

            # Check if 'touDetails' exists in item and 'touRrcMap' exists within 'touDetails'
            if "touDetails" in item and item["touDetails"].get("touRrcMap"):
                tou_rrc_map = item["touDetails"]["touRrcMap"]
                tou_details = {}

                # Factoring consumption values
                on_peak_consumption = tou_rrc_map.get("On-Peak", {}).get("tierConsKwh", 0)
                mid_peak_consumption = tou_rrc_map.get("Mid-Peak", {}).get("tierConsKwh", 0)
                off_peak_consumption = tou_rrc_map.get("Off-Peak", {}).get("tierConsKwh", 0)

                total_consumption = item["consumption"]
                total_tier_consumption = on_peak_consumption + mid_peak_consumption + off_peak_consumption

                if total_tier_consumption > 0:
                    # Calculate proportional consumption for each tier
                    on_peak_consumption = round(total_consumption * (on_peak_consumption / total_tier_consumption))
                    mid_peak_consumption = round(total_consumption * (mid_peak_consumption / total_tier_consumption))
                    off_peak_consumption = total_consumption - (on_peak_consumption + mid_peak_consumption)

                # Factoring cost values
                on_peak_cost = tou_rrc_map.get("On-Peak", {}).get("tierCost", 0)
                mid_peak_cost = tou_rrc_map.get("Mid-Peak", {}).get("tierCost", 0)
                off_peak_cost = tou_rrc_map.get("Off-Peak", {}).get("tierCost", 0)

                total_cost = item["cost"]
                total_tier_cost = on_peak_cost + mid_peak_cost + off_peak_cost

                if total_tier_cost > 0:
                    # Calculate proportional cost for each tier
                    on_peak_cost = round(total_cost * (on_peak_cost / total_tier_cost))
                    mid_peak_cost = round(total_cost * (mid_peak_cost / total_tier_cost))
                    off_peak_cost = total_cost - (on_peak_cost + mid_peak_cost)

                # Populate tou_details dictionary
                tou_details["on-peak"] = [on_peak_consumption, on_peak_cost]
                tou_details["mid-peak"] = [mid_peak_consumption, mid_peak_cost]
                tou_details["off-peak"] = [off_peak_consumption, off_peak_cost]

                # Update item with tou_details
                item["touDetails"] = tou_details
            else:
                # If 'touDetails' or 'touRrcMap' is not available, set 'touDetails' to 'unavailable'
                item["touDetails"] = "unavailable"

            
            # Check if 'tierDetails' exists in item and 'tierRrcMap' exists within 'tierDetails'
            if "tierDetails" in item and item["tierDetails"].get("tierRrcMap"):
                tier_rrc_map = item["tierDetails"]["tierRrcMap"]
                tier_details = {}

                # Factoring consumption values
                tier_consumption = {
                    "0": tier_rrc_map.get("0", {}).get("tierConsKwh", 0),
                    "1": tier_rrc_map.get("1", {}).get("tierConsKwh", 0),
                    "2": tier_rrc_map.get("2", {}).get("tierConsKwh", 0)
                }

                total_consumption = item["consumption"]
                total_tier_consumption = sum(tier_consumption.values())

                if total_tier_consumption > 0:
                    # Calculate proportional consumption for each tier
                    for tier in tier_consumption:
                        tier_consumption[tier] = round(total_consumption * (tier_consumption[tier] / total_tier_consumption))

                # Factoring cost values
                tier_cost = {
                    "0": tier_rrc_map.get("0", {}).get("tierCost", 0),
                    "1": tier_rrc_map.get("1", {}).get("tierCost", 0),
                    "2": tier_rrc_map.get("2", {}).get("tierCost", 0)
                }

                total_cost = item["cost"]
                total_tier_cost = sum(tier_cost.values())

                if total_tier_cost > 0:
                    # Calculate proportional cost for each tier
                    for tier in tier_cost:
                        tier_cost[tier] = round(total_cost * (tier_cost[tier] / total_tier_cost))

                # Populate tier_details dictionary
                for tier in tier_consumption:
                    tier_details[tier] = [tier_consumption[tier], tier_cost[tier]]

                # Update item with tier_details
                item["tierDetails"] = tier_details
            else:
                # If 'tierDetails' or 'tierRrcMap' is not available, set 'tierDetails' to 'unavailable'
                item["tierDetails"] = "unavailable"

            # Transform 'itemizationDetailsList' if it exists and is not None
            if "itemizationDetailsList" in item and item["itemizationDetailsList"] is None:
                item["itemizationDetailsList"] = "unavailable"
            elif "itemizationDetailsList" in item and item["itemizationDetailsList"] is not None:
                itemization_details = transform_itemization_details(item["itemizationDetailsList"])
                
                # Ensure all categories are present with [0, 0] for missing ones
                for category in categories:
                    if category not in itemization_details:
                        itemization_details[category] = [0, 0]
                
                if combine_categories:
                    # Combine specified categories into 'other_general_usage'
                    other_general_usage = [0, 0]
                    for category in ["cooking", "laundry", "other", "refrigeration"]:
                        consumption, cost = itemization_details.pop(category, [0, 0])
                        other_general_usage[0] += consumption
                        other_general_usage[1] += cost
                    itemization_details["otherGeneralUsage"] = other_general_usage
                    categories = [cat for cat in categories if cat not in ["cooking", "laundry", "other", "refrigeration"]]
                    categories.append("otherGeneralUsage")
                                
                # Sort the itemization details by the specified order of categories
                sorted_itemization_details = {
                    category: itemization_details[category] for category in categories
                }
                item["itemizationDetailsList"] = sorted_itemization_details
            
            # Ensure keys are in the specified order
            ordered_item = {
                "IntervalStartDate": item["intervalStartDateFormatted"],
                "IntervalEndDate": item["intervalEndDateFormatted"],
                "consumption": item.get("consumption"),
                "cost": item.get("cost"),
                "num_days": item["num_days"],
                "num_holidays": item["num_holidays"],
                "holidays": item["holidays"],
                "num_vacation": item["num_vacation"],
                "temperature": item["temperature"],
                "touDetails": item["touDetails"],
                "tierDetails": item["tierDetails"],
                "itemizationDetailsList": item.get("itemizationDetailsList", "unavailable")
            }
            
            item.clear()
            item.update(ordered_item)
        
        # Convert all floating point values to integers
        data = convert_floats_to_ints(data)

        for item in data["payload"]["usageChartDataList"]:
            item_ordered = {
                "IntervalStartDate": item["IntervalStartDate"],
                "IntervalEndDate": item["IntervalEndDate"],
                "consumption": item["consumption"],
                "cost": item["cost"],
                "num_days": item["num_days"],
                "num_holidays": item["num_holidays"],
                "num_vacation": item["num_vacation"],
                "holidays": item["holidays"],
                "temperature": item["temperature"],
                "touDetails": item["touDetails"],
                "tierDetails": item["tierDetails"],
                "itemizationDetailsList": item.get("itemizationDetailsList", "unavailable")
            }

            item.clear()
            item.update(item_ordered)

        final_data = {
            "usageChartDataList": data["payload"]["usageChartDataList"],
            "location": {
                "city": city,
                "state": state,
                "country": country,
                "zip": zipcode
            }
        }
        return final_data
        
    except KeyError as e:
        return f"KeyError: {e}"
    except TypeError as e:
        return f"TypeError: {e}"