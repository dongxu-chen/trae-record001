package com.homestay.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.homestay.common.BusinessException;
import com.homestay.common.UserContext;
import com.homestay.document.HouseDocument;
import com.homestay.dto.CalendarPriceDTO;
import com.homestay.dto.HouseSaveDTO;
import com.homestay.entity.House;
import com.homestay.entity.HouseCalendar;
import com.homestay.entity.HouseFacility;
import com.homestay.entity.HouseImage;
import com.homestay.entity.User;
import com.homestay.mapper.HouseCalendarMapper;
import com.homestay.mapper.HouseFacilityMapper;
import com.homestay.mapper.HouseImageMapper;
import com.homestay.mapper.HouseMapper;
import com.homestay.mapper.UserMapper;
import com.homestay.repository.HouseElasticsearchRepository;
import com.homestay.vo.HouseDetailVO;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.elasticsearch.core.geo.GeoPoint;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Service
public class HouseService {

    private static final String CALENDAR_VERSION_KEY = "house:calendar:version:";
    private static final String CALENDAR_DATA_KEY = "house:calendar:data:";
    private static final long CALENDAR_CACHE_EXPIRE = 1;

    @Autowired
    private HouseMapper houseMapper;

    @Autowired
    private HouseImageMapper houseImageMapper;

    @Autowired
    private HouseFacilityMapper houseFacilityMapper;

    @Autowired
    private HouseCalendarMapper houseCalendarMapper;

    @Autowired
    private UserMapper userMapper;

    @Autowired
    private HouseElasticsearchRepository houseElasticsearchRepository;

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Transactional(rollbackFor = Exception.class)
    public void saveHouse(HouseSaveDTO dto) {
        Long userId = UserContext.getUserId();
        User user = userMapper.selectById(userId);
        if (user == null || user.getHostStatus() != 1) {
            throw new BusinessException("请先成为房东");
        }
        House house = new House();
        BeanUtils.copyProperties(dto, house);
        house.setHostId(userId);
        house.setStatus(0);
        if (dto.getId() == null) {
            houseMapper.insert(house);
            initCalendar(house.getId(), house.getBasePrice());
        } else {
            House existHouse = houseMapper.selectById(dto.getId());
            if (existHouse == null || !existHouse.getHostId().equals(userId)) {
                throw new BusinessException("无权限操作");
            }
            houseMapper.updateById(house);
            houseImageMapper.delete(new LambdaQueryWrapper<HouseImage>()
                    .eq(HouseImage::getHouseId, dto.getId()));
            houseFacilityMapper.delete(new LambdaQueryWrapper<HouseFacility>()
                    .eq(HouseFacility::getHouseId, dto.getId()));
        }
        saveHouseImages(house.getId(), dto.getImages());
        saveHouseFacilities(house.getId(), dto.getFacilities());
        syncToElasticsearch(house.getId());
    }

    private void saveHouseImages(Long houseId, List<String> images) {
        if (images == null || images.isEmpty()) return;
        for (int i = 0; i < images.size(); i++) {
            HouseImage houseImage = new HouseImage();
            houseImage.setHouseId(houseId);
            houseImage.setImageUrl(images.get(i));
            houseImage.setSort(i);
            houseImageMapper.insert(houseImage);
        }
    }

    private void saveHouseFacilities(Long houseId, List<String> facilities) {
        if (facilities == null || facilities.isEmpty()) return;
        for (String facility : facilities) {
            HouseFacility houseFacility = new HouseFacility();
            houseFacility.setHouseId(houseId);
            houseFacility.setFacilityName(facility);
            houseFacility.setFacilityCode(facility);
            houseFacilityMapper.insert(houseFacility);
        }
    }

    private void initCalendar(Long houseId, java.math.BigDecimal basePrice) {
        LocalDate startDate = LocalDate.now();
        LocalDate endDate = startDate.plusYears(1);
        List<HouseCalendar> calendars = new ArrayList<>();
        for (LocalDate date = startDate; !date.isAfter(endDate); date = date.plusDays(1)) {
            HouseCalendar calendar = new HouseCalendar();
            calendar.setHouseId(houseId);
            calendar.setDate(date);
            calendar.setPrice(basePrice);
            calendar.setStock(1);
            calendar.setStatus(1);
            calendars.add(calendar);
        }
        houseCalendarMapper.batchInsert(calendars);
    }

    public void updateCalendarPrice(CalendarPriceDTO dto) {
        Long userId = UserContext.getUserId();
        House house = houseMapper.selectById(dto.getHouseId());
        if (house == null || !house.getHostId().equals(userId)) {
            throw new BusinessException("无权限操作");
        }
        LambdaQueryWrapper<HouseCalendar> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(HouseCalendar::getHouseId, dto.getHouseId());
        if (dto.getDates() != null && !dto.getDates().isEmpty()) {
            wrapper.in(HouseCalendar::getDate, dto.getDates());
        } else if (dto.getStartDate() != null && dto.getEndDate() != null) {
            wrapper.between(HouseCalendar::getDate, dto.getStartDate(), dto.getEndDate());
        }
        List<HouseCalendar> calendars = houseCalendarMapper.selectList(wrapper);
        boolean priceChanged = false;
        for (HouseCalendar calendar : calendars) {
            if (dto.getPrice() != null && !dto.getPrice().equals(calendar.getPrice())) {
                priceChanged = true;
                calendar.setPrice(dto.getPrice());
            }
            if (dto.getStock() != null) {
                calendar.setStock(dto.getStock());
            }
            if (dto.getStatus() != null) {
                calendar.setStatus(dto.getStatus());
            }
            houseCalendarMapper.updateById(calendar);
        }
        if (priceChanged || dto.getStock() != null || dto.getStatus() != null) {
            incrementCalendarVersion(dto.getHouseId());
        }
    }

    private void incrementCalendarVersion(Long houseId) {
        String versionKey = CALENDAR_VERSION_KEY + houseId;
        redisTemplate.opsForValue().increment(versionKey);
    }

    public void updateCalendarVersion(Long houseId) {
        incrementCalendarVersion(houseId);
    }

    @SuppressWarnings("unchecked")
    public List<HouseCalendar> getHouseCalendar(Long houseId, LocalDate startDate, LocalDate endDate) {
        String versionKey = CALENDAR_VERSION_KEY + houseId;
        Long version = redisTemplate.opsForValue().get(versionKey) != null
                ? Long.valueOf(redisTemplate.opsForValue().get(versionKey).toString())
                : 0L;

        String cacheKey = CALENDAR_DATA_KEY + houseId + ":" + version + ":" + startDate + ":" + endDate;

        List<HouseCalendar> cachedData = (List<HouseCalendar>) redisTemplate.opsForValue().get(cacheKey);
        if (cachedData != null) {
            return cachedData;
        }

        List<HouseCalendar> calendars = houseCalendarMapper.selectByHouseIdAndDateRange(houseId, startDate, endDate);

        redisTemplate.opsForValue().set(cacheKey, calendars, CALENDAR_CACHE_EXPIRE, TimeUnit.HOURS);

        return calendars;
    }

    public HouseDetailVO getHouseDetail(Long id) {
        House house = houseMapper.selectById(id);
        if (house == null || house.getDeleted() == 1) {
            throw new BusinessException("房源不存在");
        }
        HouseDetailVO vo = new HouseDetailVO();
        BeanUtils.copyProperties(house, vo);
        User host = userMapper.selectById(house.getHostId());
        if (host != null) {
            vo.setHostName(host.getNickname());
            vo.setHostAvatar(host.getAvatar());
        }
        List<HouseImage> images = houseImageMapper.selectList(new LambdaQueryWrapper<HouseImage>()
                .eq(HouseImage::getHouseId, id)
                .orderByAsc(HouseImage::getSort));
        vo.setImages(images.stream().map(HouseImage::getImageUrl).collect(Collectors.toList()));
        List<HouseFacility> facilities = houseFacilityMapper.selectList(new LambdaQueryWrapper<HouseFacility>()
                .eq(HouseFacility::getHouseId, id));
        vo.setFacilities(facilities.stream().map(HouseFacility::getFacilityName).collect(Collectors.toList()));
        return vo;
    }

    public void syncToElasticsearch(Long houseId) {
        House house = houseMapper.selectById(houseId);
        if (house == null || house.getDeleted() == 1) {
            houseElasticsearchRepository.deleteById(houseId);
            return;
        }
        HouseDocument document = new HouseDocument();
        BeanUtils.copyProperties(house, document);
        if (house.getLongitude() != null && house.getLatitude() != null) {
            document.setLocation(new GeoPoint(house.getLatitude().doubleValue(), house.getLongitude().doubleValue()));
        }
        List<HouseFacility> facilities = houseFacilityMapper.selectList(new LambdaQueryWrapper<HouseFacility>()
                .eq(HouseFacility::getHouseId, houseId));
        document.setFacilities(facilities.stream().map(HouseFacility::getFacilityName).collect(Collectors.toList()));
        houseElasticsearchRepository.save(document);
    }

    public void onlineHouse(Long id) {
        Long userId = UserContext.getUserId();
        House house = houseMapper.selectById(id);
        if (house == null || !house.getHostId().equals(userId)) {
            throw new BusinessException("无权限操作");
        }
        house.setStatus(1);
        houseMapper.updateById(house);
        syncToElasticsearch(id);
    }

    public void offlineHouse(Long id) {
        Long userId = UserContext.getUserId();
        House house = houseMapper.selectById(id);
        if (house == null || !house.getHostId().equals(userId)) {
            throw new BusinessException("无权限操作");
        }
        house.setStatus(0);
        houseMapper.updateById(house);
        houseElasticsearchRepository.deleteById(id);
    }
}
