package com.homestay.controller;

import com.homestay.common.Result;
import com.homestay.dto.CalendarPriceDTO;
import com.homestay.dto.HouseSaveDTO;
import com.homestay.dto.HouseSearchDTO;
import com.homestay.dto.MapHouseDTO;
import com.homestay.entity.HouseCalendar;
import com.homestay.service.HouseSearchService;
import com.homestay.service.HouseService;
import com.homestay.vo.HouseDetailVO;
import com.homestay.vo.HouseMapVO;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/house")
public class HouseController {

    @Autowired
    private HouseService houseService;

    @Autowired
    private HouseSearchService houseSearchService;

    @PostMapping("/save")
    public Result<Void> saveHouse(@Valid @RequestBody HouseSaveDTO dto) {
        houseService.saveHouse(dto);
        return Result.success();
    }

    @GetMapping("/{id}")
    public Result<HouseDetailVO> getHouseDetail(@PathVariable Long id) {
        return Result.success(houseService.getHouseDetail(id));
    }

    @PostMapping("/online/{id}")
    public Result<Void> onlineHouse(@PathVariable Long id) {
        houseService.onlineHouse(id);
        return Result.success();
    }

    @PostMapping("/offline/{id}")
    public Result<Void> offlineHouse(@PathVariable Long id) {
        houseService.offlineHouse(id);
        return Result.success();
    }

    @GetMapping("/calendar")
    public Result<List<HouseCalendar>> getHouseCalendar(@RequestParam Long houseId,
                                                         @RequestParam LocalDate startDate,
                                                         @RequestParam LocalDate endDate) {
        return Result.success(houseService.getHouseCalendar(houseId, startDate, endDate));
    }

    @PostMapping("/calendar/update")
    public Result<Void> updateCalendarPrice(@RequestBody CalendarPriceDTO dto) {
        houseService.updateCalendarPrice(dto);
        return Result.success();
    }

    @PostMapping("/search")
    public Result<Map<String, Object>> search(@RequestBody HouseSearchDTO dto) {
        return Result.success(houseSearchService.search(dto));
    }

    @PostMapping("/map")
    public Result<List<HouseMapVO>> getMapHouses(@RequestBody MapHouseDTO dto) {
        return Result.success(houseSearchService.getMapHouses(dto));
    }

    @PostMapping("/sync/{id}")
    public Result<Void> syncToElasticsearch(@PathVariable Long id) {
        houseService.syncToElasticsearch(id);
        return Result.success();
    }
}
